# MFGD
The "Mildly Friendly Git Display" team project by LB01 - Team 1B.

MFGD is a Git viewer to inspect and publicise Git repositories. It implements web-based user authentication and permissions to supports private repositories for repository access management. MFGD must be bootstrapped manually by creating an initial administrator (see installation instructions below). MFGD was implemented using Python and Django with minimal dependencies.

**WARNING:** Support for Windows is a best-effort basis which may present stability and deployment issues; MFGD was designed for deployment on a Unix-like environment (MFGD was developed under Linux).

## Deployment
### Installation
[Python 3.7+](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads) must be installed and in your **PATH** (it is recommended that Windows users install [Git BASH](https://gitforwindows.org/) to support unit testing).
Install using the below command (regular `git clone` will not clone submodule dependencies).
```term
$ git clone --recurse-submodule https://github.com/kukrimate/mfgd
```
If the repository was cloned without retrieving submodules then run the below command.
```term
$ git submodule update --init mpygit
```
Move into the cloned repository then install Python dependencies.
```term
$ python3 -m pip install -r requirements.txt --user
```

### Execution

MFGD must be bootstrapped to create the initial administrator account.
If you are deploying MFGD for **yourself** then run.
```term
$ python3 bootstrap.py
```
Otherwise, if you are deploying MFGD for demonstration purposes then setup placeholder data (this will **clone external** repositories).
```term
$ python3 populate.py
```
After installation and bootstrapping then run the below and browse to `http://localhost:8000`.
```term
$ python3 manage.py runserver
```
(see `python3 manage.py --help` to specify address and port and other configurable options).

## Unit Tests
**Warning:** Unit tests only work under Unix-like environments (including [Git BASH](https://gitforwindows.org/)) with the previously mentioned prerequisites.

Execute
```term
$ ./test.sh
```
to setup and execute the unit tests.

## External Sources

[jQuery](https://jquery.com/) is used for the repository management panel which is requested from the [Google CDN](https://developers.google.com/speed/libraries/#jquery). [Git](https://git-scm.com/) repositories are interacted with on the local filesystem using [mpygit](https://github.com/kukrimate/mpygit) (a module developed internally).
