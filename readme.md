# MFGD
The "Mildly Friendly Git Display". Team project by LB01 - Team 1B.

**NOTE**: while we do support Windows on a best effort basis, this project
was designed to run on Unix-like operating systems, thus Windows support might
have some minor issues.

## Cloning

**IMPORTANT**: clone using:

```git clone --recurse-submodule https://github.com/kukrimate/mfgd```.

Normal clones will not have a required submodule, to get a working tree
from a messed up clone run:

```git submodule update --init mpygit```.

## Running
First Python 3.7+ must be installed and **in PATH**.

After that run: ```pip install -r requirements.txt```.
This will install all the dependencies for the main application.

To run `populate.py`, git must be installed and the `git`
command present **in PATH**.

After all the prerequisits are present, first run
````python populate.py```` to create a new database.
Then the application can be started with ```python manage.py runserver```.

## Unit tests
**NOTE**: Unit tests only work on Unix-like operating system
(or Unix like environment like Cygwin, MSYS, or git bash) on Windows.

Run: `./test.sh` to create the test repositories and execute the Unit tests.
