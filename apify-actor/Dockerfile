# Apify Python base image. Pin to 3.12 for broad binary-wheel support of
# bilibili-api-python's native deps (aiohttp / lxml). See https://hub.docker.com/r/apify/.
FROM apify/actor-python:3.12

USER myuser

# Copy requirements first so dependency installation is cached across source edits.
COPY --chown=myuser:myuser requirements.txt ./

RUN echo "Python version:" \
 && python --version \
 && echo "Pip version:" \
 && pip --version \
 && echo "Installing dependencies:" \
 && pip install -r requirements.txt \
 && echo "All installed Python packages:" \
 && pip freeze

# Copy the rest of the source.
COPY --chown=myuser:myuser . ./

# Fail the build early if the wrapper has syntax errors.
RUN python -m compileall -q my_actor/

# Launch the standby MCP web server.
CMD ["python", "-m", "my_actor"]
