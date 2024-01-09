# Deploy

I assume you have Ubuntu 20.04 server with Python 3.12, `supervisor` and `memcached` (see server
setup speedrun below). In case of another Python version, change `deploy.yml` accordingly.
You will also need Ansible installed on your workstation.

1. Save your server name into `hosts` file in a current directory:

        echo MY_SERVER > hosts

2. Deploy the code:

        ./deploy.yml

3. Make sure it works as expected:

        curl http://127.0.0.1:5001/telegram

# Server setup speedrun

    sudo add-apt-repository -y -u ppa:deadsnakes/ppa \
        && sudo apt-get -y install memcached libmemcached-dev supervisor python3.12 python3.12-dev

# Check for security vulnerabilities and linter errors:

    pip install -r requirements-dev.txt
    make
