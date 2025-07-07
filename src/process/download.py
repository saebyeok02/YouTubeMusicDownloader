import multiprocessing
from src.yt_dl import create_ytdl
from pathvalidate import sanitize_filename

from src.thumbnail import edit_thumbnail
from src.gui import print_


def get_music_data(ytdl, data):
    ext = data["audio_ext"]
    music_title = sanitize_filename(data["title"])
    file_name = ytdl.prepare_filename(data)[:-len(f".{ext}")]
    thumbnail = edit_thumbnail(music_title, data["thumbnail"])
    music_data = {
        "title": music_title,
        "filename": file_name,
        "ext": ext,
    }
    if data.get("chapters") and len(data["chapters"]) > 1:
        """
        'chaters': [{'end_time': 177.0,
                     'start_time': 0.0,
                     'title': 'Stars At Dawn (明け方の星)'},
                   ]
        """
        music_data["chapters"] = data["chapters"]

    if thumbnail is not False:
        music_data["thumbnail"] = thumbnail
    return music_data


def download(url, chater_list, shared_list):
    """
    youtube url을 이용하여 해당 동영상의 음악 파일을 추출합니다. (youtube_dl)
    :param url: youtube url
    :param chater_list: 챕터별로 있는 음악을 공유하기 위한 메모리
    :param shared_list: 멀티 프로세스 간의 자원 공유를 위한 리스트
    """
    ytdl = create_ytdl()
    data = ytdl.extract_info(url, download=True)
    if 'entries' in data:
        # take items from a playlist
        data = data['entries']
    else:
        data = [data]

    for _data in data:
        queue_data = get_music_data(ytdl, _data)
        if queue_data.get("chapters"):
            chater_list.append(queue_data)
        else:
            shared_list.append(queue_data)
        print_(f"다운로드 완료 : {queue_data['title']}.{queue_data['ext']}")


def download_wrapper(queue, chater_list, shared_list):
    """
    멀티 프로세스 큐에서 작업을 할당 받고, post_processing을 실행합니다.
    :param queue: downloading_queue
    :param chater_list: 챕터별로 있는 음악을 공유 (공유메모리)
    :param shared_list: 멀티 프로세스에서 작업한 결과물 공유 (공유메모리)
    """
    url = None
    try:
        while not queue.empty():
            url = queue.get()
            download(url, chater_list, shared_list)
    except Exception as e:
        print_(f"Error downloading {url} : {e}")


def download_start(url_list, chater_list, shared_list, available_core_count, downloading_queue):
    """
    download 작업을 시작하기 위한 함수.
    :param url_list: Youtube URL List
    :param chater_list: 챕터별로 있는 음악을 공유하기 위한 메모리
    :param shared_list: 멀티 프로세스 작업 결과물을 공유하기 위한 메모리
    :param available_core_count: 멀티 프로세싱을 위한 코어 할당량 수
    :param downloading_queue: downloading_queue
    """

    for url in url_list:
        downloading_queue.put(url)

    processes = []
    for i in range(available_core_count):
        process = multiprocessing.Process(
            target=download_wrapper, args=(downloading_queue, chater_list, shared_list)
        )
        processes.append(process)
        process.daemon = True
        process.start()
        print_(f"download_{i} start")

    for process in processes:
        process.join()