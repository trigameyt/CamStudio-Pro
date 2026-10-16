"""Windows current-user DPAPI protection for the Android pairing key.

The stored token is recoverable only by the same Windows user. It is never
placed in sources, logs, README or a GitHub release.
"""
from __future__ import annotations
import base64
import ctypes
import os
from ctypes import wintypes

if os.name == 'nt':
    class DATA_BLOB(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
    _crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    _kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    _crypt.CryptProtectData.argtypes=[
        ctypes.POINTER(DATA_BLOB),ctypes.c_wchar_p,
        ctypes.POINTER(DATA_BLOB),ctypes.c_void_p,ctypes.c_void_p,
        wintypes.DWORD,ctypes.POINTER(DATA_BLOB)]
    _crypt.CryptProtectData.restype=wintypes.BOOL
    _crypt.CryptUnprotectData.argtypes=[
        ctypes.POINTER(DATA_BLOB),ctypes.c_void_p,
        ctypes.POINTER(DATA_BLOB),ctypes.c_void_p,ctypes.c_void_p,
        wintypes.DWORD,ctypes.POINTER(DATA_BLOB)]
    _crypt.CryptUnprotectData.restype=wintypes.BOOL
    _kernel.LocalFree.argtypes=[ctypes.c_void_p]
    _kernel.LocalFree.restype=ctypes.c_void_p


def _input_blob(value:bytes):
    buffer=ctypes.create_string_buffer(value)
    return DATA_BLOB(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_byte))),buffer


def _apply(value:bytes,protect:bool)->bytes:
    if os.name!='nt':
        raise RuntimeError('Protection de clé disponible uniquement sur Windows.')
    incoming,buffer=_input_blob(value)
    output=DATA_BLOB()
    fn=_crypt.CryptProtectData if protect else _crypt.CryptUnprotectData
    if protect:
        result=fn(ctypes.byref(incoming),'CamStudio Pro Android pairing key',
                  None,None,None,1,ctypes.byref(output))
    else:
        result=fn(ctypes.byref(incoming),None,None,None,None,1,ctypes.byref(output))
    if not result:
        raise OSError(ctypes.get_last_error(),'Impossible de déchiffrer la clé de cet utilisateur Windows.')
    try:
        return ctypes.string_at(output.pbData,output.cbData)
    finally:
        _kernel.LocalFree(ctypes.cast(output.pbData,ctypes.c_void_p))


def protect_key(text:str)->str:
    if not text:return ''
    return 'dpapi:' + base64.b64encode(_apply(text.encode('utf-8'),True)).decode('ascii')


def reveal_key(data:str)->str:
    if not data:return ''
    if not data.startswith('dpapi:'):
        raise ValueError('Format de clé protégée inconnu.')
    return _apply(base64.b64decode(data[6:],validate=True),False).decode('utf-8')
