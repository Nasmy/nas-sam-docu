# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM python:3.9 AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Install the function's dependencies
RUN pip install \
    --target ${FUNCTION_DIR} \
        awslambdaric

# Use a slim version of the base Python image to reduce the final image size
FROM python:3.9-slim-bullseye

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

RUN apt-get update && \
apt-get install -y curl

# Set runtime interface client as default command for the container runtime
RUN curl -Lo aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie  \
    && chmod +x aws-lambda-rie
COPY entry_script.sh /entry_script.sh
RUN chmod +x /entry_script.sh
ENTRYPOINT [ "/entry_script.sh" ]

# noninteractive apt-get
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
apt-get install -y python3-pip && \
rm -rf /var/lib/apt/lists/*


# Install python libraries
COPY requirements.txt /tmp/
RUN python3 -m pip install --upgrade pip && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt
RUN pip install -U spacy
RUN python -m spacy download en_core_web_md

# Copy function code
COPY handler.py /function
COPY . ${FUNCTION_DIR}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "handler.handler" ]