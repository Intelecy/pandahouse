FROM continuumio/miniconda3

ARG PYTHON_VERSION=3.6

RUN conda install -c conda-forge \
        python=$PYTHON_VERSION && \
    conda clean --all


ADD . /pandahouse
WORKDIR /pandahouse

RUN python3 -m pip install poetry && poetry update && poetry install

CMD poetry run pytest .
