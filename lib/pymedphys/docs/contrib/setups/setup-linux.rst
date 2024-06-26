===================================
Linux Setup
===================================

Overview
========

* Install Python 3.12.3
* Install `pipx` with ``pip install pipx``
* Install ``poetry`` with ``pipx install poetry``
* Clone the PyMedPhys git repo
* Run ``poetry install -E all`` within the root of the repo
* Run ``poetry run pre-commit install``
* Install ``pandoc`` via your package manager

  * eg. ``sudo apt-get install pandoc``

You're good to go.


Opinionated Recommendations
===========================

* Install Python with pyenv

  * `Install prerequisites`_
  * `Install pyenv`_
  * `Configure pyenv`_
* Install `VSCode`_ as your code editor
* Install `Jupyter Lab`_ to work with Notebooks


.. _`Install pyenv`: https://github.com/pyenv/pyenv-installer#install
.. _`Install prerequisites`: https://github.com/pyenv/pyenv/wiki#suggested-build-environment
.. _`VSCode`: https://code.visualstudio.com/Download
.. _`Jupyter Lab`: https://jupyterlab.readthedocs.io/en/stable/getting_started/installation.html#pip
.. _`Configure pyenv`: https://amaral.northwestern.edu/resources/guides/pyenv-tutorial
