# For testing installation on non-nixos platform
# Must be copied to project root and built from there.

FROM python:3.7

RUN useradd -ms /bin/bash user
RUN mkdir -m 0755 /nix && chown user /nix


USER user
WORKDIR /home/user
RUN echo "requests" > r


COPY . project
RUN pip install ./project
ENV PATH="/home/user/.local/bin:${PATH}"
