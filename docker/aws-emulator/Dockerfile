# AWS publishes no prebuilt AWS Emulator image; this follows
# https://docs.aws.amazon.com/emulator/latest/userguide/getting-started-docker.html
# `LTS/latest` is not pinned: the package is whatever AWS currently ships.
FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

# Use aws-emulator-aarch64.rpm on ARM hosts.
ARG EMULATOR_RPM=aws-emulator-x86_64.rpm

ADD https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/latest/${EMULATOR_RPM} /tmp/aws-emulator.rpm
RUN rpm -i /tmp/aws-emulator.rpm && rm /tmp/aws-emulator.rpm \
    && mkdir -p /home/emulator && chown 1000 /home/emulator

USER 1000
ENV HOME=/home/emulator
EXPOSE 9297
ENTRYPOINT ["aws-emulator", "-b", "0.0.0.0"]
