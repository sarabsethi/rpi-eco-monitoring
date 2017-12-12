import threading
import signal
import time


def threading_loop(out, die):

    while not die.is_set():
        print(die.is_set())
        out +=1
        print(out)
        time.sleep(1)


def exit_handler(signal, frame):
    print('{} intercepted'.format(signal))
    raise ServiceExit

class ServiceExit(Exception):
    pass

def main():

    die = threading.Event()
    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)
    t1 = threading.Thread(target=threading_loop, args=(1, die))
    t2 = threading.Thread(target=threading_loop, args=(100, die))

    try:
        print('hello')
        t1.start()
        t2.start()
        while True:
            time.sleep(0.5)

    except ServiceExit:
        die.set()
        t1.join()
        t2.join()

if __name__ == '__main__':

    main()