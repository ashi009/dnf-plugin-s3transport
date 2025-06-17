import dnf
import os
import re
import subprocess
import sys
import threading
import logging
import http.server
import socketserver
import urllib.parse
import boto3
import botocore.exceptions

logger = logging.getLogger("dnf.plugin.s3transport")


HOST_PATTERN = r"^(?P<bucket>[^.]+)\.s3\.(?P<region>[\w-]+)\.amazonaws\.com"


class S3TransportPlugin(dnf.Plugin):
    name = "s3transport"

    def __init__(self, base, cli):
        super(S3TransportPlugin, self).__init__(base, cli)
        self.base = base
        self._aws_config_file = None
        self._aws_credentials_file = None
        self._proxy_process = None
        self._proxy_url = None

    def __del__(self):
        if self._proxy_process:
            self._proxy_process.kill()
            self._proxy_process = None

    def _start_proxy_if_needed(self):
        if self._proxy_process is None:
            env = os.environ.copy()
            if self._aws_config_file:
                env["AWS_CONFIG_FILE"] = self._aws_config_file
            if self._aws_credentials_file:
                env["AWS_SHARED_CREDENTIALS_FILE"] = self._aws_credentials_file
            # Start proxy in separate process to avoid GIL contention with DNF
            self._proxy_process = subprocess.Popen(
                [sys.executable, __file__],
                env=env,
                stdout=subprocess.PIPE,
                text=True,
            )
            self._proxy_url = self._proxy_process.stdout.readline().strip()
            self._proxy_process.stdout.close()
        return self._proxy_url

    def config(self):
        conf = self.read_config(self.base.conf)
        if not conf.has_section("main") or not conf.getboolean("main", "enabled"):
            return

        if conf.has_section("aws"):
            if conf.has_option("aws", "config_file"):
                self._aws_config_file = conf.get("aws", "config_file")
            if conf.has_option("aws", "credentials_file"):
                self._aws_credentials_file = conf.get("aws", "credentials_file")

        for repo in self.base.repos.iter_enabled():
            for url in repo.baseurl:
                parsed_url = urllib.parse.urlparse(url)
                if parsed_url.scheme == "http" and re.match(
                    HOST_PATTERN, parsed_url.netloc
                ):
                    repo.proxy = self._start_proxy_if_needed()
                    break


class S3ProxyHandler(http.server.BaseHTTPRequestHandler):
    _s3_client_cache = {}
    _s3_client_cache_lock = threading.Lock()

    def log_message(self, format, *args):
        pass

    @classmethod
    def get_s3_client(cls, profile_name, region_name):
        with cls._s3_client_cache_lock:
            cache_key = (profile_name, region_name)
            if cache_key not in cls._s3_client_cache:
                args = {"region_name": region_name}
                if profile_name:
                    args["profile_name"] = profile_name
                session = boto3.Session(**args)
                cls._s3_client_cache[cache_key] = session.client("s3")
            return cls._s3_client_cache[cache_key]

    def do_GET(self):
        match = re.match(HOST_PATTERN, self.headers.get("Host"))
        if not match:
            self.send_error(400, "Bad Request: Invalid Host header")
            return
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        profile_name = query_params.get("profile", [None])[0]
        bucket_name = match.group("bucket")
        region_name = match.group("region")
        s3_key = urllib.parse.unquote(parsed_url.path.lstrip("/"))
        logger.debug(f"Processing request for Bucket='{bucket_name}', Key='{s3_key}'")
        try:
            s3 = S3ProxyHandler.get_s3_client(profile_name, region_name)
            s3_object = s3.get_object(Bucket=bucket_name, Key=s3_key)
            self.send_response(200)
            self.send_header("Content-Length", str(s3_object["ContentLength"]))
            self.send_header(
                "Content-Type", s3_object.get("ContentType", "application/octet-stream")
            )
            self.send_header(
                "Last-Modified",
                s3_object["LastModified"].strftime("%a, %d %b %Y %H:%M:%S GMT"),
            )
            self.end_headers()
            body = s3_object["Body"]
            try:
                for chunk in body.iter_chunks():
                    self.wfile.write(chunk)
            finally:
                body.close()
        except botocore.exceptions.NoCredentialsError:
            self.send_error(403, "AWS credentials not found or invalid.")
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            logger.error(
                f"S3 ClientError for Bucket='{bucket_name}', "
                f"Key='{s3_key}'. Status: {status_code}, "
                f"Code: {error_code}, Message: {error_message}"
            )
            self.send_error(status_code, f"{error_message}")
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Unexpected error processing request for Bucket='{bucket_name}', "
                f"Key='{s3_key}'. Error: {error_type} - {e}"
            )
            self.send_error(500, f"An unexpected error occurred")


def run_s3proxy_server():
    httpd = socketserver.ThreadingTCPServer(("localhost", 0), S3ProxyHandler)
    host, port = httpd.server_address
    print(f"http://{host}:{port}", flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_s3proxy_server()
