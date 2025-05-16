Name:           dnf-plugin-s3transport
Version:        {{{ git_dir_version }}}
Release:        1%{?dist}
Summary:        A DNF plugin to access repositories stored on S3

License:        MIT
URL:            https://github.com/ashi009/dnf-plugin-s3transport
VCS:            {{{ git_dir_vcs }}}
Source:         {{{ git_dir_pack }}}

BuildArch:      noarch

%description
A DNF plugin that adds support for accessing RPM repositories stored on AWS S3.
Uses boto3 to authenticate and retrieve packages from S3 buckets.

%package -n python3-%{name}
Summary:        A DNF plugin to access repositories stored on S3
%{?python_provide:%python_provide python3-%{name}}

BuildRequires:  python3-devel

Requires:       python3-dnf
Requires:       python3-boto3

%description -n python3-%{name}
A DNF plugin that adds support for accessing RPM repositories stored on AWS S3.
Uses boto3 to authenticate and retrieve packages from S3 buckets.

%prep
{{{ git_dir_setup_macro }}}

%build
# No build required

%install
# Install the plugin directly
mkdir -p %{buildroot}%{python3_sitelib}/dnf-plugins
install -p -m 644 s3transport.py %{buildroot}%{python3_sitelib}/dnf-plugins/

# Install the config file
mkdir -p %{buildroot}%{_sysconfdir}/dnf/plugins
install -p -m 644 s3transport.conf %{buildroot}%{_sysconfdir}/dnf/plugins/

%files -n python3-%{name}
%license LICENSE
%doc README.md
%{python3_sitelib}/dnf-plugins/s3transport.py
%{python3_sitelib}/dnf-plugins/__pycache__/s3transport.*
%config(noreplace) %{_sysconfdir}/dnf/plugins/s3transport.conf

%changelog
{{{ git_dir_changelog }}}
