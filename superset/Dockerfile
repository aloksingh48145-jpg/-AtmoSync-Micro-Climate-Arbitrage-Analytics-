# Extends the base Superset image with the Snowflake driver, so Superset
# can connect to IOT_DB directly. The stock apache/superset image does not
# ship with snowflake-sqlalchemy pre-installed.

FROM apache/superset:3.1.0

USER root
RUN pip install --no-cache-dir --default-timeout=120 --retries=5 snowflake-sqlalchemy==1.6.1 && \
    pip install --no-cache-dir --default-timeout=120 --retries=5 "cryptography>=41.0.2,<41.1.0"
USER superset
