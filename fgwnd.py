import os
import operator
import itertools
import functools
import win32api
import win32con
import win32gui
import win32process


class txn(list):
    def __call__(self, o):
        for f in self:
            o = f(o)
        return o


class llel(list):
    def __call__(*args, **kwds):
        self, *args = args
        yield from (f(*args, **kwds) for f in self)
        return None


def getwndpid(hwnd):
    return win32process.GetWindowThreadProcessId(hwnd)[1]


def iterwnd(hidden=None):
    hwnd = win32gui.GetForegroundWindow()
    while hwnd:
        if hidden or win32gui.IsWindowVisible(hwnd):
            yield hwnd
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
    return None


def iterwindow(callback, skip=None, *, ppid=None):
    if None is skip:
        ppid = ppid or os.getppid()
        skip = True
    skip = int(skip)
    callback = functools.lru_cache(maxsize=1)(callback)
    iterable = iter(iterwnd(hidden=False))
    if skip:
        iterable = itertools.dropwhile(txn((callback, operator.not_)),
                                       iterable)
        iterable = itertools.chain(
            itertools.dropwhile(
                txn((llel((txn(
                    (getwndpid, functools.partial(operator.eq, ppid))),
                           callback)), all)) if ppid else callback,
                itertools.islice(iterable, skip)), iterable)
    yield from filter(callback, iterable)
    return None


def getprocname(pid):
    hProcess = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION,
                                    False, pid)
    return win32process.GetModuleFileNameEx(hProcess, None)


def _main(args=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--skip', type=int)
    subparsers = parser.add_subparsers(dest='method', required=True)
    parser_name = subparsers.add_parser('name')
    parser_name.add_argument('name')
    parser_class = subparsers.add_parser('class')
    parser_class.add_argument('name')
    options = parser.parse_args(args=args)
    if 'name' == options.method:
        import pathlib
        method = txn(
            (getwndpid, getprocname, pathlib.Path(options.name).samefile))
    elif 'class' == options.method:
        method = txn(
            (win32gui.GetClassName, functools.partial(operator.eq,
                                                      options.name)))
    for hwnd in iterwindow(method, skip=options.skip):
        print('{:08x}'.format(hwnd))
    return None


if '__main__' == __name__:
    _main()
