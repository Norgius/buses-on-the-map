# Автобусы на карте Москвы

Веб-приложение показывает передвижение автобусов на карте Москвы.

<img src="screenshots/buses.gif">

## Как установить

Вам понадобится Python версии 3.10 или старше. Для установки пакетов рекомендуется создать виртуальное окружение.

Первым шагом установите пакеты:

```python3
pip install -r requirements.txt
```

## О backend файлах

На текущий момент серверная часть реализована через сохраненные данные координат автобусов. Они лежат в папке `routes`.

Главный сервер, а точнее `2 сервера` сосредоточены в файле `server.py`.

Первый сервер отвечает за обработку поступающих данных с сервера `fake_bus.py`. Второй же отправляет данные в сам браузер.

### Аргументы `server.py`

Для того, чтобы узнать информацию об аргументах `server.py`, выполните команду:
```
python server.py --help
```
Аргументы по-умолчанию:
* Адрес сервера для автобусов: `127.0.0.1`
* Адрес сервера для клиента: `127.0.0.1`
* Порт для автобусов: `8080`
* Порт для клиента: `8000`

### Аргументы `fake_bus.py`

Чтобы узнать об аргументах, выполните:
```
python fake_bus.py --help
```
Аргументы по-умолчанию:
* Адрес сервера: `ws://127.0.0.1:8080`
* Количество маршрутов: `500`
* Количество автобусов на каждом маршруте: `3`
* Количество открытых веб-сокетов: `5`
* Задержка в обновлении координат: `1` секунда
* Префикс к busId: `не указан`

## Тестирование

Для проверки работоспособности на проекте есть тесты в папке `tests/`

Запустите сервер командой:
```
python server.py -l
```
После запустите сами тесты:
```
pytest ./tests 
```

## Как запустить backend

Выполните команду для запуска 2-х серверов:
```
python server.py -l
``` 
Следующей командой вы начнёте отправлять данные о перемещении автобусов:
```
python fake_bus.py -l
```

## Как запустить frontend

- Откройте в браузере файл index.html

## Настройки frontend

Внизу справа на странице можно включить отладочный режим логгирования и указать нестандартный адрес веб-сокета.

<img src="screenshots/settings.png">

Настройки сохраняются в Local Storage браузера и не пропадают после обновления страницы. Чтобы сбросить настройки удалите ключи из Local Storage с помощью Chrome Dev Tools —> Вкладка Application —> Local Storage.

Если что-то работает не так, как ожидалось, то начните с включения отладочного режима логгирования.

## Формат данных

Фронтенд ожидает получить от сервера JSON сообщение со списком автобусов:

```js
{
  "msgType": "Buses",
  "buses": [
    {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
    {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"},
  ]
}
```

Те автобусы, что не попали в список `buses` последнего сообщения от сервера будут удалены с карты.

Фронтенд отслеживает перемещение пользователя по карте и отправляет на сервер новые координаты окна:

```js
{
  "msgType": "newBounds",
  "data": {
    "east_lng": 37.65563964843751,
    "north_lat": 55.77367652953477,
    "south_lat": 55.72628839374007,
    "west_lng": 37.54440307617188,
  },
}
```

## Используемые библиотеки

- [Leaflet](https://leafletjs.com/) — отрисовка карты
- [loglevel](https://www.npmjs.com/package/loglevel) для логгирования

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).
