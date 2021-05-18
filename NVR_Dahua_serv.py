# -*- coding: utf-8 -*-
from dahua_rpc import DahuaRpc
import eventlet
import socketio
from datetime import datetime


sio = socketio.Server(engineio_logger=False)
app = socketio.WSGIApp(sio)

HOST, PORT = 'localhost', 5000


def sort_data(res, start_time, end_time, camera):
    """ формировка данных json """
    data = {"result": {"data": []}}
    if res['result']:
        c_num = None
        found = res['params']['found']
        save_count = -1
        for counter in range(found):

            # данные об архиве
            camera_channel = res['params']['infos'][counter]['Channel']
            disk = res['params']['infos'][counter]['Disk']
            cluster = res['params']['infos'][counter]['Cluster']
            length = res['params']['infos'][counter]['Length']
            c_time = res['params']['infos'][counter]['StartTime']
            url_path = "http://{}/cgi-bin/RPC_Loadfile{}".format(camera, res['params']['infos'][counter]['FilePath'])
            partition = res['params']['infos'][counter]['Partition']
            types = res['params']['infos'][counter]['Type']
            if types == 'dav':
                flags = res['params']['infos'][counter]['Flags']
                vs = res['params']['infos'][counter]['VideoStream']
            else:
                flags, vs = '', ''
            new_info = {'Disk': disk, 'Cluster': cluster, 'Length': length, 'CreationTime': c_time, 'URL': url_path,
                        'Flags': flags, 'Partition': partition, 'Type': types, 'VideoStream': vs}

            if c_num == camera_channel:

                data['result']['data'][save_count]['info'].append(new_info)
            else:
                data['result']['data'].append({'Channel': camera_channel, 'info': [new_info]})
                c_num = camera_channel
                save_count += 1

    else:
        found = 0
    data['result'].update({"found": found})       # количество найденных элементов
    data['result'].update({"Start": start_time})  # начало отрезка времени
    data['result'].update({"End": end_time})      # конец отрезка времени
    return data


@sio.event
def get_data(sid, dahua_data):
    print(f"Попытка подключение к камере {dahua_data['camera']['hostname']}")
    # данные камеры
    dahua = DahuaRpc(host=dahua_data['camera']['hostname'],
                     username=dahua_data['camera']['login'],
                     password=dahua_data['camera']['password'])
    try:
        # при успешном логин камеры
        if dahua.login():
            print(f"Подключене c камерой {dahua_data['camera']['hostname']} установлено")
            # ролучение ид для поиска
            object_id = dahua.get_media_file_info()['result']

            # объявление данных
            start_time = '2021-01-01 00:00:00' \
                if dahua_data['camera']['params']['start_time'] == '' \
                else dahua_data['camera']['params']['start_time']
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") \
                if dahua_data['camera']['params']['end_time'] == '' \
                else dahua_data['camera']['params']['end_time']
            channel = -1 \
                if dahua_data['camera']['params']['channel'] == '' \
                else dahua_data['camera']['params']['channel']
            types = '*' \
                if dahua_data['camera']['params']['type'] == '' \
                else dahua_data['camera']['params']['type']
            count = 10000 \
                if dahua_data['camera']['params']['count'] == '' \
                else dahua_data['camera']['params']['count']

            # пойск по параметрам и сохранение в data
            dahua.start_find_media_file(object_id=object_id,
                                        start=start_time,
                                        end=end_time,
                                        channel=channel,
                                        types=types
                                        )
            data = dahua.find_next_media_file(object_id=object_id,
                                              count=count)
            # логаут с камеры
            dahua.stop_find_media_file(object_id=object_id)
            dahua.destroy_find_media_file(object_id=object_id)
            dahua.logout()

            # обработка данных в json. можно отправить и без обработки:
            # return data['params'] # убарть коммент
            data = sort_data(data, start_time, end_time, dahua_data['camera']['hostname'])

            # отправка данных через sio. emit
            # send_message(sid, data) # убарть коммент

            del dahua
            return data

        # если не удалось залогиниться
        else:
            del dahua
            # print(f"Подключене c камерой {dahua_data['camera']['hostname']} НЕ установлено")
            return {'error': "Неверный логин или пароль"}
    except Exception as e:
        # ЗАМЕТКА любая ошибка при выполнение пойска (кроме ошибок связанных с json)
        # print(f"Камера {dahua_data['camera']['hostname']}\nСообщение ошибки: {e}")
        return {'error': e}


def send_message(sid, msg):
    """ отправка сообщения клиенту """
    print(f'Отправка данных на {sid}')
    sio.emit('my_response', msg, room=sid)


@sio.on('connect')
def connect(sid, eventlet):
    print(f'Установлено подключение с {sid}')


@sio.on('disconnect')
def disconnect(sid):
    sio.disconnect(sid)


if __name__ == '__main__':
    # запуск сервера
    eventlet.wsgi.server(eventlet.listen((HOST, PORT)), app)
