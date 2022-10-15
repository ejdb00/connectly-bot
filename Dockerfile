FROM python:3.10

# INSTALL DEPENDENCIES
RUN curl -sL https://deb.nodesource.com/setup_17.x | bash - \
    && apt-get update \
    && apt-get install --yes \
    # App dependencies
    runit \
    nginx \
    && rm -rf /var/lib/apt/lists/*
    
# INSTALL NGINX CONFIG
RUN rm /etc/nginx/sites-enabled/default
RUN rm /etc/nginx/sites-available/default
COPY nginx-http.conf /etc/nginx/sites-enabled/bot-http
COPY nginx-https.conf /etc/nginx/sites-enabled/bot-https

# INSTALL PYTHON PACKAGES
WORKDIR /usr/src/bot
ADD bot/requirements.txt ./
RUN pip install -r requirements.txt

# COPY SOURCE CODE
WORKDIR /usr/src/bot
ADD bot/ ./

# CONFIGURE
EXPOSE 8080
EXPOSE 8443
WORKDIR /usr/src