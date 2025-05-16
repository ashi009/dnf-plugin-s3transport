# DNF S3Transport Plugin

A [DNF](https://github.com/rpm-software-management/dnf) plugin that adds support for accessing RPM repositories stored on AWS S3.

## Features

- Access S3 buckets using AWS credentials
- Support for AWS profiles
- Works with standard DNF repository configuration

## Installation

### From COPR

```
dnf copr enable ashi009/dnf-plugin-s3transport
dnf install python3-dnf-plugin-s3transport
```

## Usage

Create a repository configuration in `/etc/yum.repos.d/` that points to your S3 bucket:

```ini
[s3-example]
name=S3 Example
baseurl=http://bucket-name.s3.region-code.amazonaws.com/path?profile=profile
enabled=1
gpgcheck=0
```

The base URL must be in the format `http://bucket-name.s3.region-code.amazonaws.com/path?profile=profile`, where:

- `bucket-name` is the name of your S3 bucket
- `region-code` is the AWS region code (e.g., `us-east-1`, `eu-west-1`)
- `path` is the path to the RPM repository within the bucket
- `profile=profile` parameter is optional and specifies which AWS profile to use from your AWS configuration.

## Configuration

The plugin's configuration file is located at `/etc/dnf/plugins/s3transport.conf`:

```ini
[main]
enabled=1

[aws]
config_file=/etc/aws/config
```

The `config_file` parameter in the `[aws]` section is optional. If not specified, the plugin uses the default AWS configuration location.
