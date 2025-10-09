%bcond_with python3

%global srcname urllib3

Name:           python-%{srcname}
Version:        1.24.2
Release:        4%{?dist}
Summary:        Python HTTP library with thread-safe connection pooling and file post

License:        MIT
URL:            https://github.com/shazow/urllib3
Source0:        %{url}/archive/%{version}/%{srcname}-%{version}.tar.gz
# Used with Python 3.5+
Source1:        ssl_match_hostname_py3.py
BuildArch:      noarch

# CVE-2019-11236 python-urllib3:
#   - CRLF injection due to not encoding the '\r\n' sequence leading to
#     possible attack on internal service.
#   - Also known as CVE-2019-9740 (duplicate entry)
# Backported from:
#  * https://github.com/urllib3/urllib3/pull/1591
#    - Superfluous commits were omitted (flake8 checks, travis settings, macos patch)
#  * https://github.com/urllib3/urllib3/pull/1593
Patch1:         CVE-2019-11236.patch

# CVE-2020-26137
# CRLF injection via HTTP request method
# Resolved upstream: https://github.com/urllib3/urllib3/pull/1800
Patch2: CVE-2020-26137.patch

# CVE-2023-43804
# Added the `Cookie` header to the list of headers to strip from
# requests when redirecting to a different host. As before, different headers
# can be set via `Retry.remove_headers_on_redirect`.
# Tests backported only partially as we don't use the whole part of
# testing with dummyserver.
# Tracking bug: https://bugzilla.redhat.com/show_bug.cgi?id=2242493
# Upstream fix: https://github.com/urllib3/urllib3/commit/01220354d389cd05474713f8c982d05c9b17aafb
Patch3: CVE-2023-43804.patch

%description
Python HTTP module with connection pooling and file POST abilities.

%package -n python2-%{srcname}
Summary:        Python2 HTTP library with thread-safe connection pooling and file post
%{?python_provide:%python_provide python2-%{srcname}}

Requires:       ca-certificates

# Previously bundled things:
Requires:       python2-six
Requires:       python2-backports-ssl_match_hostname

# Secure extra requirements
Requires:       python2-ipaddress
Requires:       python2-pysocks

BuildRequires:  python2-devel

# For tests
BuildRequires:  python2-pytest
BuildRequires:  python2-mock
BuildRequires:  python2-pysocks
BuildRequires:  python2-backports-ssl_match_hostname

%description -n python2-%{srcname}
Python2 HTTP module with connection pooling and file POST abilities.


%if %{with python3}
%package -n python3-%{srcname}
Summary:        Python3 HTTP library with thread-safe connection pooling and file post

BuildRequires:  python3-devel
# For unittests
BuildRequires:  python3-mock
BuildRequires:  python3-six
BuildRequires:  python3-pysocks
BuildRequires:  python3-pytest

Requires:       ca-certificates
Requires:       python3-six
Requires:       python3-pysocks

%description -n python3-%{srcname}
Python3 HTTP module with connection pooling and file POST abilities.

%endif

%prep
%setup -q -n %{srcname}-%{version}

%patch1 -p1
%patch2 -p1
%patch3 -p1

# Drop the dummyserver tests in koji.
# These require tornado, a Web framework otherwise unused in the distro.
rm -rf test/with_dummyserver/
rm -rf test/test_connectionpool.py
rm -rf dummyserver/
# Don't run the Google App Engine tests
rm -rf test/appengine/
# Lots of these tests started failing, even for old versions, so it has something
# to do with Fedora in particular. They don't fail in upstream build infrastructure
rm -rf test/contrib/

# Tests for Python built without SSL, but RHEL builds with SSL. These tests
# fail when combined with the unbundling of backports-ssl_match_hostname
rm -f test/test_no_ssl.py

# Make sure that the RECENT_DATE value doesn't get too far behind what the current date is.
# RECENT_DATE must not be older that 2 years from the build time, or else test_recent_date
# (from test/test_connection.py) would fail. However, it shouldn't be to close to the build time either,
# since a user's system time could be set to a little in the past from what build time is (because of timezones,
# corner cases, etc). As stated in the comment in src/urllib3/connection.py:
#   When updating RECENT_DATE, move it to within two years of the current date,
#   and not less than 6 months ago.
#   Example: if Today is 2018-01-01, then RECENT_DATE should be any date on or
#   after 2016-01-01 (today - 2 years) AND before 2017-07-01 (today - 6 months)
# There is also a test_ssl_wrong_system_time test (from test/with_dummyserver/test_https.py) that tests if
# user's system time isn't set as too far in the past, because it could lead to SSL verification errors.
# That is why we need RECENT_DATE to be set at most 2 years ago (or else test_ssl_wrong_system_time would
# result in false positive), but before at least 6 month ago (so this test could tolerate user's system time being
# set to some time in the past, but not to far away from the present).
# Next few lines update RECENT_DATE dynamically.

recent_date=$(date --date "7 month ago" +"%Y, %_m, %_d")
sed -i "s/^RECENT_DATE = datetime.date(.*)/RECENT_DATE = datetime.date($recent_date)/" src/urllib3/connection.py


%build
%py2_build
%if %{with python3}
%py3_build
%endif


%install
%py2_install
%if %{with python3}
%py3_install
%endif

# Unbundle the Python 2 build
rm -rf %{buildroot}/%{python2_sitelib}/urllib3/packages/six.py*
rm -rf %{buildroot}/%{python2_sitelib}/urllib3/packages/ssl_match_hostname/

mkdir -p %{buildroot}/%{python2_sitelib}/urllib3/packages/
ln -s %{python2_sitelib}/six.py %{buildroot}/%{python2_sitelib}/urllib3/packages/six.py
ln -s %{python2_sitelib}/six.pyc %{buildroot}/%{python2_sitelib}/urllib3/packages/six.pyc
ln -s %{python2_sitelib}/six.pyo %{buildroot}/%{python2_sitelib}/urllib3/packages/six.pyo

ln -s %{python2_sitelib}/backports/ssl_match_hostname %{buildroot}/%{python2_sitelib}/urllib3/packages/ssl_match_hostname

%if %{with python3}
# Unbundle the Python 3 build
rm -rf %{buildroot}/%{python3_sitelib}/urllib3/packages/six.py*
rm -rf %{buildroot}/%{python3_sitelib}/urllib3/packages/__pycache__/six*
rm -rf %{buildroot}/%{python3_sitelib}/urllib3/packages/ssl_match_hostname/

mkdir -p %{buildroot}/%{python3_sitelib}/urllib3/packages/
ln -s %{python3_sitelib}/six.py \
      %{buildroot}/%{python3_sitelib}/urllib3/packages/six.py
ln -s %{python3_sitelib}/__pycache__/six.cpython-%{python3_version_nodots}.opt-1.pyc \
      %{buildroot}/%{python3_sitelib}/urllib3/packages/__pycache__/
ln -s %{python3_sitelib}/__pycache__/six.cpython-%{python3_version_nodots}.pyc \
      %{buildroot}/%{python3_sitelib}/urllib3/packages/__pycache__/
# urllib3 requires Python 3.5 to use the standard library's match_hostname,
# which we ship in RHEL8, so we can safely replace the bundled version with
# this stub which imports the necessary objects.
cp %{SOURCE1} %{buildroot}/%{python3_sitelib}/urllib3/packages/ssl_match_hostname.py
%endif

%check
pushd test
PYTHONPATH=%{buildroot}%{python2_sitelib}:%{python2_sitelib} %{__python2} -m pytest -v
popd
%if %{with python3}
py.test-3
%endif

%files -n python2-%{srcname}
%license LICENSE.txt
%doc CHANGES.rst README.rst CONTRIBUTORS.txt
%{python2_sitelib}/urllib3/
%{python2_sitelib}/urllib3-*.egg-info


%if %{with python3}
%files -n python3-%{srcname}
%license LICENSE.txt
%doc CHANGES.rst README.rst CONTRIBUTORS.txt
%{python3_sitelib}/urllib3/
%{python3_sitelib}/urllib3-*.egg-info
%endif


%changelog
* Thu Oct 12 2023 Lumír Balhar <lbalhar@redhat.com> - 1.24.2-4
- Security fix for CVE-2023-43804
Resolves: RHEL-11993

* Thu Nov 12 2020 Tomas Orsava <torsava@redhat.com> - 1.24.2-3
- Update RECENT_DATE dynamically
Related: rhbz#1883890 rhbz#1761380

* Fri Oct 09 2020 Charalampos Stratakis <cstratak@redhat.com> - 1.24.2-2
- Security fix for CVE-2020-26137
Resolves: rhbz#1883890

* Fri May 03 2019 Tomas Orsava <torsava@redhat.com> - 1.24.2-1
- Rebased to 1.24.2 to fix CVE-2019-11324
- Added patches for CVE-2019-11236 (AKA CVE-2019-9740)
- Resolves: rhbz#1706765 rhbz#1706762

* Thu Apr 25 2019 Tomas Orsava <torsava@redhat.com> - 1.23-7
- Bumping due to problems with modular RPM upgrade path
- Resolves: rhbz#1695587

* Tue Jul 31 2018 Lumír Balhar <lbalhar@redhat.com> - 1.23-6
- Make possible to disable python3 subpackage

* Mon Jul 16 2018 Lumír Balhar <lbalhar@redhat.com> - 1.23-5
- First version for python27 module
