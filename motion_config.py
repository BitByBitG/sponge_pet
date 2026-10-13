"""INI motion settings. Missing or invalid values use individual defaults."""
import configparser
import math


def read_motion_config(path):
    parser=configparser.ConfigParser(inline_comment_prefixes=(';','#'))
    try:
        parser.read(path,encoding='utf-8-sig')
    except (OSError,UnicodeError,configparser.Error):
        parser=configparser.ConfigParser()
    settings={}
    for section,key,default in [('animation','walk_fps',5),('animation','eat_fps',3),
                                ('movement','walk_speed',65),('movement','follow_speed',220)]:
        try:
            value=parser.getfloat(section,key)
            if not math.isfinite(value) or value<=0:raise ValueError()
        except (ValueError,configparser.Error):
            value=default
        settings[key]=value
    return settings
