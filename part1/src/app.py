import os
import json
import datetime
import decimal
import time
import redis_lock
import pickle
import threading
import signal

from flask import Flask, request, Response
from redis import Redis
from hashlib import md5

host_redis = os.environ.get('HOST_REDIS', 'redis')
port_redis = os.environ.get('PORT_REDIS', 6379)

app = Flask(__name__)
redis = Redis(host=host_redis, port=port_redis)

lock = redis_lock.Lock(redis, "Redis_Lock")

@app.route('/')
def hello():
    return 'It\'s Working!!!'

@app.route('/v1/products', methods=['POST'])
def products():
    try:
        if redis_manipulate(md5(request.data).digest()):
            return JsonFormater.json_result(200, {'state': 'Sucess', 'message': 'Recebido com sucesso'})
        return JsonFormater.json_result(403, {'state': 'Sucess', 'message': 'Dados já recebidos recentemente'})
    except Exception as e:
        return JsonFormater.json_result(500, {'state': 'error', 'message': e})


def redis_manipulate(r_data):
    status = True
    requests_list = None
    lock.acquire()
    if redis.exists("requests"):
        requests_list = pickle.loads(redis.get('requests'))
        for r in requests_list:
            if time.time() - r['TimeStamp'] < 600 and r['request'] == r_data:
                status = False
        if status:
            requests_list.append({"TimeStamp": time.time(), "request":  r_data})
    else:
        requests_list = [{"TimeStamp": time.time(), "request":  r_data}]
    if status:
        redis.set('requests', pickle.dumps(requests_list))
    
    lock.release()
    return status


def requests_cache_control():
    while True:
        status = True
        new_requests_list = []
        lock.acquire()
        if redis.exists("requests"):
            requests_list = pickle.loads(redis.get('requests'))
            app.logger.info(requests_list)
            for r in requests_list:
                if time.time() - r['TimeStamp'] < 600:
                    new_requests_list.append(r)
        redis.set('requests', pickle.dumps(new_requests_list))
        
        lock.release()
        time.sleep(60)

def finalize(signum, desc):
    os._exit(0)


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date) or isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return (datetime.datetime.min + obj).time().isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        else:
            return super(self.__class__, self).default(obj)


class JsonFormater:
    def json_result(_code, _body):
        response = json.dumps(_body, cls=EnhancedJSONEncoder)
        callback = request.args.get('callback')
        if callback is not None:
            response = callback + "({})".format(response)

        return Response(response, mimetype='application/json'), _code


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, finalize)
    signal.signal(signal.SIGINT, finalize)

    cache_control = threading.Thread(target=requests_cache_control)
    cache_control.start()

    app.run(host='0.0.0.0', port=8880, debug=True)