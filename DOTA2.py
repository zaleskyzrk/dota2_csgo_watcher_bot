#!/usr/bin/python
# -*- coding: UTF-8 -*-
import requests
import json
from DOTA2_dicts import *
import random
import time
import message_sender
api_key = "2B469C11A7D6FF2D0E97D2347FA1AF28"


# 根据slot判断队伍, 返回1为天辉, 2为夜魇
def get_team_by_slot(slot):
    if slot < 100:
        return 1
    else:
        return 2


def get_last_match_id_by_short_steamID(short_steamID):
    # get match_id
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v001/?key={}' \
          '&account_id={}&matches_requested=1'.format(api_key, short_steamID)
    match_id = json.loads(requests.get(url).content)["result"]["matches"][0]["match_id"]
    return match_id


def get_match_detail_info(match_id):
    # get match detail
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/' \
          '?key={}&match_id={}'.format(api_key, match_id)
    match_info = json.loads(requests.get(url).content)["result"]

    return match_info


# 接收某局比赛的玩家列表, 生成开黑战报
# 参数为玩家对象列表和比赛ID
def generate_party_message(match_id, player_list):
    match = get_match_detail_info(match_id=match_id)

    # 比赛模式
    mode_id = match["game_mode"]
    if mode_id in (15, 19):  # 各种活动模式不通报
        return
    mode = GAME_MODE[mode_id] if mode_id in GAME_MODE else '未知'

    lobby_id = match['lobby_type']
    lobby = LOBBY[lobby_id] if lobby_id in LOBBY else '未知'

    player_num = len(player_list)
    # 更新玩家对象的比赛信息
    for i in player_list:
        for j in match['players']:
            if i.short_steamID == j['account_id']:
                i.dota2_kill = j['kills']
                i.dota2_death = j['deaths']
                i.dota2_assist = j['assists']
                i.kda = ((1. * i.kill + i.assist) / i.death) if i.death != 0 else (1. * i.kill + i.assist)

                i.dota2_team = get_team_by_slot(j['player_slot'])
                i.hero = j['hero_id']
                i.last_hit = j['last_hits']
                i.damage = j['hero_damage']
                i.gpm = j['gold_per_min']
                break

    # 队伍信息
    team = player_list[0].dota2_team
    team_damage = 0
    team_kills = 0
    team_deaths = 0
    for i in match['players']:
        if get_team_by_slot(i['player_slot']) == team:
            team_damage += i['hero_damage']
            team_kills += i['kills']
            team_deaths += i['deaths']

    win = False
    if match['radiant_win'] and team == 1:
        win = True
    elif not match['radiant_win'] and team == 2:
        win = True
    elif match['radiant_win'] and team == 2:
        win = False
    elif not match['radiant_win'] and team == 1:
        win = False

    nicknames = ''
    if player_num >= 3:
        for i in range(player_num - 1):
            nicknames += player_list[i].nickname
            nicknames += ', '
    else:
        nicknames += player_list[0].nickname

    nicknames += '和'
    nicknames += player_list[player_num - 1].nickname

    top_kda = 0
    for i in player_list:
        if i.kda > top_kda:
            top_kda = i.kda

    if (win and top_kda > 10) or (not win and top_kda > 6):
        postive = True
    elif (win and top_kda < 4) or (not win and top_kda < 1):
        postive = False
    else:
        if random.randint(0, 1) == 0:
            postive = True
        else:
            postive = False

    print_str = ''
    if win and postive:
        print_str += random.choice(WIN_POSTIVE_PARTY).format(nicknames) + '\n'
    elif win and not postive:
        print_str += random.choice(WIN_NEGATIVE_PARTY).format(nicknames) + '\n'
    elif not win and postive:
        print_str += random.choice(LOSE_POSTIVE_PARTY).format(nicknames) + '\n'
    else:
        print_str += random.choice(LOSE_NEGATIVE_PARTY).format(nicknames) + '\n'

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(match['start_time']))
    duration = match['duration']
    print_str += "开始时间: {}\n".format(start_time)
    print_str += "持续时间: {:.0f}分{:.0f}秒\n".format(duration / 60, duration % 60)

    print_str += '游戏模式: [{}/{}]\n'.format(mode, lobby)

    for i in player_list:
        nickname = i.nickname
        hero = HEROES_LIST_CHINESE[i.hero] if i.hero in HEROES_LIST_CHINESE else '不知道什么鬼'
        kda = i.kda
        last_hits = i.last_hits
        damage = i.hero_damage
        kills, deaths, assists = i.kills, i.deaths, i.assists
        gpm, xpm = i.gpm, i.xpm

        damage_rate = 0 if team_damage == 0 else (100 * (float(damage) / team_damage))
        participation = 0 if team_kills == 0 else (100 * float(kills + assists) / team_kills)
        deaths_rate = 0 if team_deaths == 0 else (100 * float(deaths) / team_deaths)

        print_str += "{}使用{}, KDA: {:.2f}[{}/{}/{}], GPM/XPM: {}/{}, " \
                     "补刀数: {}, 总伤害: {}({:.2f}%), 参战率: {:.2f}%, 参葬率: {:.2f}%\n" \
            .format(nickname, hero, kda, kills, deaths, assists, gpm, xpm, last_hits,
                    damage, damage_rate, participation, deaths_rate)

    print_str += "战绩详情: https://cn.dotabuff.com/matches/{}".format(match_id)

    # print(print_str)
    message_sender.message(print_str)


# 接收某局比赛的玩家信息, 生成单排战报
# 参数为玩家对象
def generate_solo_message(match_id, player_obj):
    match = get_match_detail_info(match_id=match_id)

    # 比赛模式
    mode_id = match["game_mode"]
    if mode_id in (15, 19):  # 各种活动模式不通报
        return
    mode = GAME_MODE[mode_id] if mode_id in GAME_MODE else '未知'

    lobby_id = match['lobby_type']
    lobby = LOBBY[lobby_id] if lobby_id in LOBBY else '未知'

    # 更新玩家对象的比赛信息
    for j in match['players']:
        if player_obj.short_steamID == j['account_id']:
            player_obj.dota2_kill = j['kills']
            player_obj.dota2_death = j['deaths']
            player_obj.dota2_assist = j['assists']
            player_obj.kda = ((1. * player_obj.kill + player_obj.assist) / player_obj.death)\
                if player_obj.death != 0 else (1. * player_obj.kill + player_obj.assist)

            player_obj.dota2_team = get_team_by_slot(j['player_slot'])
            player_obj.hero = j['hero_id']
            player_obj.last_hit = j['last_hits']
            player_obj.damage = j['hero_damage']
            player_obj.gpm = j['gold_per_min']
            break

    # 队伍信息
    team = player_obj.dota2_team
    team_damage = 0
    team_kills = 0
    team_deaths = 0
    for i in match['players']:
        if get_team_by_slot(i['player_slot']) == team:
            team_damage += i['hero_damage']
            team_kills += i['kills']
            team_deaths += i['deaths']

    win = False
    if match['radiant_win'] and team == 1:
        win = True
    elif not match['radiant_win'] and team == 2:
        win = True
    elif match['radiant_win'] and team == 2:
        win = False
    elif not match['radiant_win'] and team == 1:
        win = False

    if (win and player_obj.kda > 10) or (not win and player_obj.kda > 6):
        postive = True
    elif (win and player_obj.kda < 4) or (not win and player_obj.kda < 1):
        postive = False
    else:
        if random.randint(0, 1) == 0:
            postive = True
        else:
            postive = False

    print_str = ''
    if win and postive:
        print_str += random.choice(WIN_POSTIVE_PARTY).format(player_obj.nickname) + '\n'
    elif win and not postive:
        print_str += random.choice(WIN_NEGATIVE_PARTY).format(player_obj.nickname) + '\n'
    elif not win and postive:
        print_str += random.choice(LOSE_POSTIVE_PARTY).format(player_obj.nickname) + '\n'
    else:
        print_str += random.choice(LOSE_NEGATIVE_PARTY).format(player_obj.nickname) + '\n'

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(match['start_time']))
    duration = match['duration']
    print_str += "开始时间: {}\n".format(start_time)
    print_str += "持续时间: {:.0f}分{:.0f}秒\n".format(duration // 60, duration % 60)

    print_str += '游戏模式: [{}/{}]\n'.format(mode, lobby)

    nickname = player_obj.nickname
    hero = HEROES_LIST_CHINESE[player_obj.hero] if player_obj.hero in HEROES_LIST_CHINESE else '不知道什么鬼'
    kda = player_obj.kda
    last_hits = player_obj.last_hits
    damage = player_obj.hero_damage
    kills, deaths, assists = player_obj.kills, player_obj.deaths, player_obj.assists
    gpm, xpm = player_obj.gpm, player_obj.xpm

    damage_rate = 0 if team_damage == 0 else (100 * (float(damage) / team_damage))
    participation = 0 if team_kills == 0 else (100 * float(kills + assists) / team_kills)
    deaths_rate = 0 if team_deaths == 0 else (100 * float(deaths) / team_deaths)

    print_str += "{}使用{}, KDA: {:.2f}[{}/{}/{}], GPM/XPM: {}/{}, " \
                 "补刀数: {}, 总伤害: {}({:.2f}%), 参战率: {:.2f}%, 参葬率: {:.2f}%\n" \
        .format(nickname, hero, kda, kills, deaths, assists, gpm, xpm, last_hits,
                damage, damage_rate, participation, deaths_rate)

    print_str += "战绩详情: https://cn.dotabuff.com/matches/{}".format(match_id)

    # print(print_str)
    message_sender.message(print_str)