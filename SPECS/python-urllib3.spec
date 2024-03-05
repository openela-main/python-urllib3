%global srcname urllib3

Name:           python-%{srcname}
Version:        1.24.2
Release:        5%{?dist}.2
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

# Enable post-handshake authentication for TLS 1.3
# - https://github.com/urllib3/urllib3/issues/1634
# - https://bugzilla.redhat.com/show_bug.cgi?id=1726743
Patch2:         Enable_TLS_1.3_post-handshake_authentication.patch

# CVE-2020-26137
# CRLF injection via HTTP request method
# Resolved upstream: https://github.com/urllib3/urllib3/pull/1800
Patch3: CVE-2020-26137.patch

# CVE-2023-43804
# Added the `Cookie` header to the list of headers to strip from
# requests when redirecting to a different host. As before, different headers
# can be set via `Retry.remove_headers_on_redirect`.
# Tests backported only partially as we don't use the whole part of
# testing with dummyserver.
# Tracking bug: https://bugzilla.redhat.com/show_bug.cgi?id=2242493
# Upstream fix: https://github.com/urllib3/urllib3/commit/01220354d389cd05474713f8c982d05c9b17aafb
Patch4: CVE-2023-43804.patch

# CVE-2023-45803
# Remove HTTP request body when request method is changed.
# Tracking bug: https://bugzilla.redhat.com/show_bug.cgi?id=CVE-2023-45803
# Upstream fix: https://github.com/urllib3/urllib3/commit/4e98d57809dacab1cbe625fddeec1a290c478ea9
Patch5: CVE-2023-45803.patch

%description
Python HTTP module with connection pooling and file POST abilities.


%package -n python3-%{srcname}
Summary:        Python3 HTTP library with thread-safe connection pooling and file post

BuildRequires:  python3-devel
# For unittests
BuildRequires:  python3-nose
BuildRequires:  python3-mock
BuildRequires:  python3-six
BuildRequires:  python3-pysocks
BuildRequires:  python3-pytest

Requires:       ca-certificates
Requires:       python3-six
Requires:       python3-pysocks

%description -n python3-%{srcname}
Python3 HTTP module with connection pooling and file POST abilities.


%prep
%setup -q -n %{srcname}-%{version}

%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1
%patch5 -p1

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

%build
%py3_build


%install
%py3_install

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


%check
pushd test
PYTHONPATH=%{buildroot}%{python3_sitelib}:%{python3_sitelib} %{__python3} -m pytest -v
popd


%files -n python3-%{srcname}
%license LICENSE.txt
%doc CHANGES.rst README.rst CONTRIBUTORS.txt
%{python3_sitelib}/urllib3/
%{python3_sitelib}/urllib3-*.egg-info


%changelog
* Tue Dec 12 2023 Lumír Balhar <lbalhar@redhat.com> - 1.24.2-5.2
- Security fix for CVE-2023-45803
Resolves: RHEL-16871

* Thu Oct 12 2023 Lumír Balhar <lbalhar@redhat.com> - 1.24.2-5.1
- Security fix for CVE-2023-43804
Resolves: RHEL-17861

* Mon Nov 09 2020 Charalampos Stratakis <cstratak@redhat.com> - 1.24.2-5
- Security fix for CVE-2020-26137
Resolves: rhbz#1883889

* Wed Oct 30 2019 Anna Khaitovich <akhaitov@redhat.com> - 1.24.2-4
- Update RECENT_DATE dynamically
Resolves: rhbz#1761380

* Wed Aug 28 2019 Lumír Balhar <lbalhar@redhat.com> - 1.24.2-3
- Enable TLS 1.3 post-handshake authentication
- Adjust RECENT_DATE variable according to rules
Resolves: rhbz#1726743

* Wed May 22 2019 Tomas Orsava <torsava@redhat.com> - 1.24.2-2
- Rebuilding after gating was enabled
- Resolves: rhbz#1703361 rhbz#1706026

* Fri May 03 2019 Tomas Orsava <torsava@redhat.com> - 1.24.2-1
- Rebased to 1.24.2 to fix CVE-2019-11324
- Added patches for CVE-2019-11236 (AKA CVE-2019-9740)
- Resolves: rhbz#1703361 rhbz#1706026

* Wed Jul 11 2018 Petr Viktorin <pviktori@redhat.com> - 1.23-5
- Remove the Python 2 subpackage
  https://bugzilla.redhat.com/show_bug.cgi?id=1590400

* Mon Jun 25 2018 Lumír Balhar <lbalhar@redhat.com> - 1.23-4
- Allow build with Python 2

* Wed Jun 20 2018 Petr Viktorin <pviktori@redhat.com> - 1.23-3
- Skip tests that require tornado

* Wed Jun 20 2018 Lumír Balhar <lbalhar@redhat.com> - 1.23-2
- Remove unneeded python3-psutil dependency

* Tue Jun 05 2018 Jeremy Cline <jeremy@jcline.org> - 1.23-1
- Update to the latest upstream release (rhbz 1586072)

* Tue May 22 2018 Petr Viktorin <pviktori@redhat.com> - 1.22-10
- Skip tests for python2 subpackage, due to missing dependencies (rhbz 1580882)

* Thu May 03 2018 Lukas Slebodnik <lslebodn@fedoraproject.org> - 1.22-9
- Do not lowercase hostnames with custom-protocol (rhbz 1567862)
- upstream: https://github.com/urllib3/urllib3/issues/1267

* Wed Apr 18 2018 Jeremy Cline <jeremy@jcline.org> - 1.22-8
- Drop the dependency on idna and cryptography (rhbz 1567862)

* Mon Apr 16 2018 Jeremy Cline <jeremy@jcline.org> - 1.22-7
- Drop the dependency on PyOpenSSL, it's not needed (rhbz 1567862)

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.22-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Wed Jan 31 2018 Iryna Shcherbina <ishcherb@redhat.com> - 1.22-5
- Update Python 2 dependency declarations to new packaging standards
  (See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3)

* Thu Jan 25 2018 Tomas Hoger <thoger@redhat.com> - 1.22-4
- Fix FTBFS - Move RECENT_DATE to 2017-06-30

* Fri Dec 01 2017 Jeremy Cline <jeremy@jcline.org> - 1.22-3
- Symlink the Python 3 bytecode for six (rbhz 1519147)

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.22-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Jul 21 2017 Jeremy Cline <jeremy@jcline.org> - 1.22-1
- Update to 1.22 (#1473293)

* Wed May 17 2017 Jeremy Cline <jeremy@jcline.org> - 1.21.1-1
- Update to 1.21.1 (#1445280)

* Thu Feb 09 2017 Jeremy Cline <jeremy@jcline.org> - 1.20-1
- Update to 1.20 (#1414775)

* Tue Dec 13 2016 Stratakis Charalampos <cstratak@redhat.com> - 1.19.1-2
- Rebuild for Python 3.6

* Thu Nov 17 2016 Jeremy Cline <jeremy@jcline.org> 1.19.1-1
- Update to 1.19.1
- Clean up the specfile to only support Fedora 26

* Wed Aug 10 2016 Kevin Fenzi <kevin@scrye.com> - 1.16-3
- Rebuild now that python-requests is ready to update.

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.16-2
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Wed Jun 15 2016 Kevin Fenzi <kevin@scrye.com> - 1.16-1
- Update to 1.16

* Thu Jun 02 2016 Ralph Bean <rbean@redhat.com> - 1.15.1-3
- Create python2 subpackage to comply with guidelines.

* Wed Jun 01 2016 Ralph Bean <rbean@redhat.com> - 1.15.1-2
- Remove broken symlinks to unbundled python3-six files
  https://bugzilla.redhat.com/show_bug.cgi?id=1295015

* Fri Apr 29 2016 Ralph Bean <rbean@redhat.com> - 1.15.1-1
- Removed patch for ipv6 support, now applied upstream.
- Latest version.
- New dep on pysocks.

* Fri Feb 26 2016 Ralph Bean <rbean@redhat.com> - 1.13.1-3
- Apply patch from upstream to fix ipv6.

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1.13.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Dec 21 2015 Ralph Bean <rbean@redhat.com> - 1.13.1-1
- new version

* Fri Dec 18 2015 Ralph Bean <rbean@redhat.com> - 1.13-1
- new version

* Mon Dec 14 2015 Ralph Bean <rbean@redhat.com> - 1.12-1
- new version

* Thu Oct 15 2015 Robert Kuska <rkuska@redhat.com> - 1.10.4-7
- Rebuilt for Python3.5 rebuild

* Sat Oct 10 2015 Ralph Bean <rbean@redhat.com> - 1.10.4-6
- Sync from PyPI instead of a git checkout.

* Tue Sep 08 2015 Ralph Bean <rbean@redhat.com> - 1.10.4-5.20150503gita91975b
- Drop requirement on python-backports-ssl_match_hostname on F22 and newer.

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.10.4-4.20150503gita91975b
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Mon Jun 08 2015 Ralph Bean <rbean@redhat.com> - 1.10.4-3.20150503gita91975b
- Apply pyopenssl injection for an outdated cpython as per upstream advice
  https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning
  https://urllib3.readthedocs.org/en/latest/security.html#pyopenssl

* Tue May 19 2015 Ralph Bean <rbean@redhat.com> - 1.10.4-2.20150503gita91975b
- Specify symlinks for six.py{c,o}, fixing rhbz #1222142.

* Sun May 03 2015 Ralph Bean <rbean@redhat.com> - 1.10.4-1.20150503gita91975b
- Latest release for python-requests-2.7.0

* Wed Apr 29 2015 Ralph Bean <rbean@redhat.com> - 1.10.3-2.20150429git585983a
- Grab a git snapshot to get around this chunked encoding failure.

* Wed Apr 22 2015 Ralph Bean <rbean@redhat.com> - 1.10.3-1
- new version

* Thu Feb 26 2015 Ralph Bean <rbean@redhat.com> - 1.10.2-1
- new version

* Wed Feb 18 2015 Ralph Bean <rbean@redhat.com> - 1.10.1-1
- new version

* Wed Feb 18 2015 Ralph Bean <rbean@redhat.com> - 1.10.1-1
- new version

* Mon Jan 05 2015 Ralph Bean <rbean@redhat.com> - 1.10-2
- Copy in a shim for ssl_match_hostname on python3.

* Sun Dec 14 2014 Ralph Bean <rbean@redhat.com> - 1.10-1
- Latest upstream 1.10, for python-requests-2.5.0.
- Re-do unbundling without patch, with symlinks.
- Modernize python2 macros.
- Remove the with_dummyserver tests which fail only sometimes.

* Wed Nov 05 2014 Ralph Bean <rbean@redhat.com> - 1.9.1-1
- Latest upstream, 1.9.1 for latest python-requests.

* Mon Aug  4 2014 Tom Callaway <spot@fedoraproject.org> - 1.8.2-4
- fix license handling

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.8.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed May 14 2014 Bohuslav Kabrda <bkabrda@redhat.com> - 1.8.2-2
- Rebuilt for https://fedoraproject.org/wiki/Changes/Python_3.4

* Mon Apr 21 2014 Arun S A G <sagarun@gmail.com> - 1.8.2-1
- Update to latest upstream version

* Mon Oct 28 2013 Ralph Bean <rbean@redhat.com> - 1.7.1-2
- Update patch to find ca_certs in the correct location.

* Wed Sep 25 2013 Ralph Bean <rbean@redhat.com> - 1.7.1-1
- Latest upstream with support for a new timeout class and py3.4.

* Wed Aug 28 2013 Ralph Bean <rbean@redhat.com> - 1.7-3
- Bump release again, just to push an unpaired update.

* Mon Aug 26 2013 Ralph Bean <rbean@redhat.com> - 1.7-2
- Bump release to pair an update with python-requests.

* Thu Aug 22 2013 Ralph Bean <rbean@redhat.com> - 1.7-1
- Update to latest upstream.
- Removed the accept-header proxy patch which is included in upstream now.
- Removed py2.6 compat patch which is included in upstream now.

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.5-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jun 11 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 1.5-6
- Fix Requires of python-ordereddict to only apply to RHEL

* Fri Mar  1 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 1.5-5
- Unbundling finished!

* Fri Mar 01 2013 Ralph Bean <rbean@redhat.com> - 1.5-4
- Upstream patch to fix Accept header when behind a proxy.
- Reorganize patch numbers to more clearly distinguish them.

* Wed Feb 27 2013 Ralph Bean <rbean@redhat.com> - 1.5-3
- Renamed patches to python-urllib3-*
- Fixed ssl check patch to use the correct cert path for Fedora.
- Included dependency on ca-certificates
- Cosmetic indentation changes to the .spec file.

* Tue Feb  5 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 1.5-2
- python3-tornado BR and run all unittests on python3

* Mon Feb 04 2013 Toshio Kuratomi <toshio@fedoraproject.org> 1.5-1
- Initial fedora build.
