#!/usr/bin/env bash
#cd /opt/webgenai
#PYTHONPATH=$PWD python database/manager.py -K
#cd -
#gunicorn --log-level=info -b 0.0.0.0:${APILOGICPROJECT_PORT} --timeout 60 -w1 -t1 --reload alsr:flask_app
source /opt/webgenai/database/models/util/util.sh
export PYTHONPATH="$PWD:${PYTHONPATH}"
export APILOGICSERVER_CHATGPT_APIKEY=NA
export APILOGICPROJECT_PORT=${APILOGICPROJECT_PORT:-5656}
export APILOGICPROJECT_SWAGGER_PORT=${APILOGICPROJECT_SWAGGER_PORT:-8282}
export APILOGICPROJECT_API_PREFIX="${APILOGICPROJECT_API_PREFIX}"

function start_container() {
    # Only in GenAI-Logic Products
    set -e
    set -x
    cd /opt/webgenai/container-mgr/
    # create container
    python client.py create "${PROJECT_ID}" "${APILOGICPROJECT_PORT}" 8282
    #ctr_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'  "${PROJECT_ID}")
    #sleep 1
    #ctr_ip=$(python -c "import socket;print(socket.gethostbyname('${PROJECT_ID}'))")
    # use the container IP in the nginx config
    #sed -i -e 's/localhost:/$backend:/g' -e 's/set $backend ".*";/set $backend "'"${ctr_ip}"'";/' "/opt/projects/wgadmin/nginx/${PROJECT_ID}.conf"
    nginx -s reload
}

LOG_FILE="./logs/run.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# export GUNICORN_CMD_ARGS="--log-level=info --bind=0.0.0.0:${APILOGICPROJECT_PORT} --timeout=60 --workers=1 --threads=1 --reload"

# gunicorn api_logic_server_run:flask_app 2>&1 | while read line
# do
#     echo "${line}" | grep -qE "Logic Bank Activation Error:"
#     if [[ $? -eq 0 ]]; then
#         APILOGICPROJECT_DISABLE_RULES=1 gunicorn api_logic_server_run:flask_app
#     fi
#     echo "${line}" >&2
# done

# exit

[[ "${GENAI_LOGIC_PROD}" == "true" ]] && grep -q '^set $backend' "/opt/projects/wgadmin/nginx/${PROJECT_ID}.conf"
if [[ $? == 0 ]]; then
    start_container
    exit
fi

LOGICBANK_FAILSAFE=true FLASK_DEBUG=1 python api_logic_server_run.py