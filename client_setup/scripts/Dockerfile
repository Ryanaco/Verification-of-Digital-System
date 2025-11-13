# ===============================================================================================
#
# SyoSil
#
# ===============================================================================================

# ---------------------------
# Icarus base image
# ---------------------------

FROM ubuntu:22.04 AS builder-icarus

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && \
    apt-get install -y --no-install-recommends\
    --reinstall ca-certificates \
    # icarus requirements
    make \
    automake \
    autoconf \
    bison \
    flex \
    gperf \
    build-essential \
    zlib1g-dev \
    # because of v11: configure: error: C preprocessor "/lib/cpp" fails sanity check
    g++ \
    libreadline-dev \
    #
    git \
    gtkwave \
	&& \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set temporary Working directory for icarus verilog installation
RUN mkdir -p /tmp/iverilog
WORKDIR /home/

# Setup ARG variables (Not available after container is built)
# tag names: 'v11_0'| 'v12_0' | 'master'
ARG IVERILOG_VERSION='v12_0'
ARG IVERILOG_REPO_URL='https://github.com/steveicarus/iverilog.git'

RUN git clone --branch=${IVERILOG_VERSION} ${IVERILOG_REPO_URL} --depth 1 --single-branch /tmp/iverilog && \
    cd /tmp/iverilog && \
    # bash autoconf.sh && \
    autoconf && \
    ./configure && \
    # make && \
    make check && \
    make install && \
    cd && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ENTRYPOINT ["/usr/local/bin/iverilog"]

RUN echo "ICARUS image DONE"

# ===============================================================================================

# ---------------------------
# Main image
# ---------------------------

FROM builder-icarus AS syosil-base

# ARGS to be used because of X11 in WSL
ARG DISPLAY
ARG WAYLAND_DISPLAY
ARG XDG_RUNTIME_DIR
ARG PULSE_SERVER

ENV LANG=C.UTF-8
ENV DISPLAY=${DISPLAY}
ENV WAYLAND_DISPLAY=${WAYLAND_DISPLAY}
ENV XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR}
ENV PULSE_SERVER=${PULSE_SERVER}

ARG USERNAME
ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends \
    python3.10-minimal \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    #
    # because of pyucis-viewer
    libxcb-xinerama0 libqt5x11extras5 \
    #
    vim \
    nano \
    emacs \
	&& \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV USERNAME=${USERNAME?student}
ENV USER_UID=${USER_UID?1000}
ENV USER_GID=${USER_GID?1000}

ENV PYTHON_H_HOME='/usr/include/python3.10'
ENV PYTHONPATH='/usr/lib/python3'

RUN echo "MAIN ${USERNAME}"

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd -ms /bin/bash ${USERNAME} --gid ${USER_GID} --uid $USER_UID

USER ${USERNAME}

# Add some colour to the terminal
ENV TERM="xterm-256color"
ENV PS1='\e[92m\u\e[0m@\e[94m\h\e[0m:\e[35m\w\e[0m# '

# Set Working directory
WORKDIR /home/${USERNAME}

# copy testing script, release, and result checking script into docker, only relevant for release testing
# copy-release
# copy-test-script
# copy-check-results

RUN echo "alias python='/usr/bin/python3'" >> /home/${USERNAME}/.bashrc

# This is an harded coded message to show that the container was started
# Maybe there is a better approach for this
ENV HELLO_MSG="\n\
\necho ============================================== \
\necho Welcome to the Syosil Docker container!!! \
\necho ============================================== \
\necho \
\n \
"
RUN echo ${HELLO_MSG} >> /home/${USERNAME}/.bashrc

# Start an interactive bash shell when the container runs
CMD ["/bin/bash", "-l"]

RUN echo "MAIN image DONE"

# ===============================================================================================
