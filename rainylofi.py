import subprocess
import socket
import os
import time
import json
import sys
import curses # For TUI
import random

# --- Configuration ---
LOFI_STREAM_URL = "https://www.youtube.com/watch?v=jfKfPfyJRdk"
RAIN_SOUND_FILE = "./rain.ogg"
STORM_SOUND_FILE = "./storm.ogg"

SOCKET_DIR = "/tmp"
def get_socket_path(name):
    return os.path.join(SOCKET_DIR, f"mpv_{name}_{os.getpid()}.socket")

# --- Animation Configuration ---
RAIN_CHARS = ['|', ':', '.', "'"]
NOTE_CHARS = ['♪', '♫', '♩', '♬', '♭', '♮', '♯']
MAX_RAIN_DROPS_PER_WIDTH_UNIT = 0.36
MIN_NEW_RAIN_DROPS_PER_FRAME = 1
MAX_NEW_RAIN_DROPS_PER_FRAME = 6
MAX_NOTES_PER_WIDTH_UNIT = 0.08
LIGHTNING_CHANCE = 0.06
LIGHTNING_DURATION_FRAMES = 3
LIGHTNING_BRANCH_CHANCE = 0.4
LIGHTNING_MAX_BRANCHES = 2
LIGHTNING_BRANCH_MAX_LEN = 5
NOTE_MAX_FLOAT_LINES = 4
NOTE_FLOAT_SPEED = 0.3
RAIN_SPAWN_Y_PERCENT = 0.2

# --- UI Layout Configuration ---
TITLE_H = 1
TRACK_INFO_H = 3
TRACK_INFO_HLINE_H = 1
DEFAULT_INSTRUCTIONS_AREA_H = 3
FEEDBACK_H_IN_INSTRUCTIONS = 1
MIN_ANIMATION_H = 2

MIN_FULL_UI_W = 70
COLOR_PURPLE_CUSTOM_ID = 16

SOUND_PRESETS = {
    '1': {"name": "Chill Focus", "settings": {
        "lofi": {"playing": True, "volume": 60}, "rain": {"playing": True, "volume": 30}, "storm": {"playing": False, "volume": 0}}},
    '2': {"name": "Study Storm", "settings": {
        "lofi": {"playing": True, "volume": 40}, "rain": {"playing": True, "volume": 70}, "storm": {"playing": True, "volume": 70}}},
    '3': {"name": "Quiet Lofi", "settings": {
        "lofi": {"playing": True, "volume": 50}, "rain": {"playing": False, "volume": 0}, "storm": {"playing": False, "volume": 0}}},
    '0': {"name": "Silence All", "settings": {
        "lofi": {"playing": False, "volume": 0}, "rain": {"playing": False, "volume": 0}, "storm": {"playing": False, "volume": 0}}},
}
HELP_LINES_TEXT = [
    "[L]ofi: Play/Pause  [O] Vol+  [K] Vol-",
    "[R]ain: Play/Pause  [E] Vol+  [D] Vol-",
    "[S]torm:Play/Pause  [T] Vol+  [G] Vol-",
    "Presets: [1]Chill [2]Study [3]Lofi [0]Mute",
    "[H]elp Toggle    [Q]uit Player"
]
HELP_DISPLAY_DURATION_FRAMES = 70

PLAYER_TITLE = " ♪ Rainy Lofi ♪ "

# --- Internet Check ---
def check_internet_connection(host="8.8.8.8", port=53, timeout=2):
    original_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except socket.error:
        return False
    finally:
        socket.setdefaulttimeout(original_timeout)

# --- MPV Control Functions ---
def start_mpv_instance(sound_type_key, sound_states, mpv_processes):
    params = sound_states[sound_type_key]
    media_source = params["media"]
    ipc_socket = params["socket"]

    sound_states[sound_type_key]["_file_not_found"] = False
    sound_states[sound_type_key]["_mpv_not_found"] = False
    if sound_type_key == "lofi":
        sound_states[sound_type_key]["_no_internet"] = False

    if sound_type_key != "lofi" and not os.path.exists(media_source):
        sound_states[sound_type_key]["is_running"] = False
        sound_states[sound_type_key]["_file_not_found"] = True
        return None

    if sound_type_key == "lofi":
        if not check_internet_connection():
            sound_states[sound_type_key]["is_running"] = False
            sound_states[sound_type_key]["_no_internet"] = True
            return None

    if os.path.exists(ipc_socket):
        try:
            os.remove(ipc_socket)
        except OSError:
            pass

    command = ["mpv", f"--input-ipc-server={ipc_socket}", "--vo=null", "--video=no", "--no-terminal",
               "--force-window=no", f"--volume={sound_states[sound_type_key]['volume']}", media_source]
    if sound_type_key == "lofi":
        command.extend(["--idle=yes", "--loop-file=no"])
    else:
        command.append("--loop-file=inf")

    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        mpv_processes[sound_type_key] = process
        sound_states[sound_type_key]["is_running"] = True

        socket_wait_retries = 30 if sound_type_key == "lofi" else 20
        for _ in range(socket_wait_retries):
            if os.path.exists(ipc_socket):
                is_paused = not sound_states[sound_type_key]["playing"]
                if is_paused:
                    time.sleep(0.2)
                    send_mpv_command(ipc_socket, {"command":["set_property","pause",True]})
                return process
            time.sleep(0.1)

        sound_states[sound_type_key]["is_running"] = False
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=0.5)
        return None
    except FileNotFoundError:
        sound_states[sound_type_key].update({"is_running":False,"_mpv_not_found":True})
        return None
    except Exception:
        sound_states[sound_type_key]["is_running"]=False
        return None

def send_mpv_command(ipc_socket, command_obj):
    if not os.path.exists(ipc_socket):
        return {"error": "socket not found"}
    try:
        cs=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        cs.settimeout(0.2)
        cs.connect(ipc_socket)
        cs.sendall(json.dumps(command_obj).encode('utf-8')+b'\n')
        cs.close()
        return {"status": "success"}
    except socket.timeout:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

def set_sound_state(stype, play_target, vol_target, s_states, mpv_procs):
    state = s_states[stype]
    original_playing_state = state.get("playing", False)
    original_volume = state.get("volume", 0)

    state["playing"] = play_target
    state["volume"] = vol_target

    if not state.get("is_running", False):
        if play_target:
            start_mpv_instance(stype, s_states, mpv_procs)
            if not state.get("is_running", False):
                state["playing"] = original_playing_state
                state["volume"] = original_volume
                if stype == "lofi" and state.get("_no_internet"):
                    return "Lofi: No internet connection."
                if state.get("_mpv_not_found"):
                    return f"{stype.capitalize()}: mpv not found."
                if state.get("_file_not_found"):
                    return f"{stype.capitalize()}: File not found."
                return f"{stype.capitalize()} failed to start."
            return f"{stype.capitalize()} starting..."
        else:
            return f"{stype.capitalize()} state set (offline)."

    send_mpv_command(state["socket"],{"command":["set_property","volume",vol_target]})
    target_mpv_pause_state = not play_target
    send_mpv_command(state["socket"],{"command":["set_property","pause",target_mpv_pause_state]})

    if play_target:
        return f"{stype.capitalize()} set to play (vol: {vol_target}%)."
    else:
        return f"{stype.capitalize()} set to pause/stop (vol: {vol_target}%)."


def toggle_play_pause(stype, s_states, mpv_procs):
    state = s_states[stype]
    new_desired_play_state = not state["playing"]

    if state.get("is_running", False):
        mpv_pause_command = not new_desired_play_state
        res = send_mpv_command(state["socket"], {"command": ["set_property", "pause", mpv_pause_command]})
        if res.get("status") == "success":
            state["playing"] = new_desired_play_state
            return f"{stype.capitalize()}: {'Playing' if state['playing'] else 'Paused'}"
        else:
            return f"Err Toggling {stype.capitalize()}:{res.get('error','Unk')[:15]}"
    else:
        return set_sound_state(stype, new_desired_play_state, state["volume"], s_states, mpv_procs)


def adjust_volume(stype, change, s_states):
    state=s_states[stype]
    new_vol=max(0,min(100,state["volume"]+change))
    state["volume"]=new_vol

    if not state.get("is_running",False):
        return f"{stype.capitalize()} Vol set to {new_vol}% (offline)."

    res=send_mpv_command(state["socket"],{"command":["set_property","volume",new_vol]})
    if res.get("status")=="success":
        return f"{stype.capitalize()} Vol {'+'if change>0 else ''}{change}% ({new_vol}%)"
    return f"Err {stype.capitalize()} Vol:{res.get('error','Unk')[:15]}"

def apply_preset(pkey, s_states, mpv_procs):
    if pkey not in SOUND_PRESETS:
        return "Invalid preset."
    preset=SOUND_PRESETS[pkey]
    for stype,settings in preset["settings"].items():
        if stype in s_states:
            set_sound_state(stype, settings["playing"], settings["volume"], s_states, mpv_procs)
    return f"Preset '{preset['name']}' applied."


# --- Curses UI Functions ---
def get_volume_bar(volume, width):
    if width < 2:
        return ""
    bar_chars_width = width - 2
    if bar_chars_width < 0: bar_chars_width = 0
    filled_len = int(bar_chars_width * volume / 100)
    empty_len = bar_chars_width - filled_len
    return f"[{'█' * filled_len}{'─' * empty_len}]"

def draw_track_info_line(stdscr, y, name, state, w, c_main, c_err):
    try:
        sym = "▶ " if state["playing"] else "❚❚"
        lcol = c_main
        xtra = ""
        if not state.get("is_running", False):
            sym = "✖ "
            lcol = c_err
            if state.get("_file_not_found"): xtra=f"(File {os.path.basename(state['media'])} nf)"
            elif state.get("_mpv_not_found"): xtra="(mpv nf)"
            elif state.get("_no_internet"): xtra="(No Internet)"
            elif state.get("playing") is True:
                xtra = "(Start Failed)"
            else: xtra="(Not Run)"

        vol_percent_str = f"{state['volume']:>3}%"
        part1 = f"  {name.upper():<7} {sym} {vol_percent_str} "
        remaining_width_for_bar_and_extra = w - 2 - len(part1)

        extra_len_with_space = len(xtra) + (1 if xtra else 0)
        available_for_bar = remaining_width_for_bar_and_extra - extra_len_with_space

        vol_bar_str = get_volume_bar(state["volume"], max(3, available_for_bar))
        full_line_content = f"{part1}{vol_bar_str} {xtra}".strip()

        stdscr.attron(curses.color_pair(lcol))
        stdscr.addstr(y, 2, full_line_content[:w-4])
        stdscr.attroff(curses.color_pair(lcol))
    except curses.error:
        pass

def _draw_char_safe(stdscr, y, x, char, color_attr):
    try:
        stdscr.addch(y, x, char, color_attr)
    except curses.error:
        pass

def _generate_lightning_bolt(anim_width, anim_height):
    points = []; x = random.randint(0, anim_width - 1); path_char = random.choice(['\\', '/', '|'])
    for y_coord in range(anim_height):
        points.append((x, y_coord, path_char if path_char != '|' else random.choice(['|',':'])))
        x_change = (random.choice([-1,0,0,1]) if random.random()<0.3 else 0) if path_char=='|' else random.choice([-1,0,1,(1 if path_char=='/' else -1)])
        x = max(0, min(anim_width - 1, x + x_change))
        if x_change == -1: path_char = '\\'
        elif x_change == 1: path_char = '/'
        else: path_char = '|' if random.random() < 0.7 else path_char
        if 0 < y_coord < anim_height -1 and random.random() < LIGHTNING_BRANCH_CHANCE:
            branches = 0
            for _ in range(LIGHTNING_MAX_BRANCHES):
                if random.random() < 0.5 and branches < LIGHTNING_MAX_BRANCHES :
                    bx, by, bdx = x, y_coord, random.choice([-1,1]); bchar = '/' if bdx == 1 else '\\'
                    for _i in range(random.randint(1, LIGHTNING_BRANCH_MAX_LEN)):
                        bx += bdx; by += 1
                        if not (0 <= bx < anim_width and 0 <= by < anim_height):
                            break
                        points.append((bx, by, bchar))
                        if random.random() < 0.3:
                            break
                    branches +=1
    return points

def update_and_draw_animations(stdscr,y_s,a_h,x_s,a_w,s_s,anim_s,c_cfg):
    if a_w <= 0 or a_h <= 0:
        return
    for i in range(a_h):
        try:
            stdscr.addstr(y_s + i, x_s, " " * a_w)
        except curses.error:
            pass
    if s_s["storm"]["playing"] and s_s["storm"].get("is_running", False):
        sc=curses.color_pair(c_cfg["lightning"])
        if anim_s["lightning_bolt"]:
            for lx,ly,lc in anim_s["lightning_bolt"]["points"]:
                _draw_char_safe(stdscr,y_s+ly,x_s+lx,lc,sc)
            anim_s["lightning_bolt"]["frames_left"]-=1
            if anim_s["lightning_bolt"]["frames_left"]<=0:
                anim_s["lightning_bolt"]=None
        elif random.random()<LIGHTNING_CHANCE and a_w>0 and a_h>=MIN_ANIMATION_H:
            anim_s["lightning_bolt"]={"points":_generate_lightning_bolt(a_w,a_h),"frames_left":LIGHTNING_DURATION_FRAMES}

    if s_s["rain"]["playing"] and s_s["rain"].get("is_running", False):
        rc=curses.color_pair(c_cfg["rain"])
        nd=[(x,y+1,c) for x,y,c in anim_s["rain_drops"] if y+1<a_h]
        anim_s["rain_drops"]=nd
        v=s_s["rain"]["volume"]
        f=0 if v<=50 else (v-50)/50.0
        nn=int(MIN_NEW_RAIN_DROPS_PER_FRAME+f*(MAX_NEW_RAIN_DROPS_PER_FRAME-MIN_NEW_RAIN_DROPS_PER_FRAME))
        nnd=random.randint(min(nn,MAX_NEW_RAIN_DROPS_PER_FRAME//2),nn)
        mt=int(a_w*MAX_RAIN_DROPS_PER_WIDTH_UNIT)
        syl=max(1,int(a_h*RAIN_SPAWN_Y_PERCENT))
        for _ in range(nnd):
            if len(anim_s["rain_drops"])<mt and a_w>0:
                anim_s["rain_drops"].append((random.randint(0,a_w-1),random.randint(0,syl-1),random.randint(0,len(RAIN_CHARS)-1)))
        for x,y,c in anim_s["rain_drops"]:
            _draw_char_safe(stdscr,y_s+y,x_s+x,RAIN_CHARS[c],rc)

    if s_s["lofi"]["playing"] and s_s["lofi"].get("is_running", False):
        lc = curses.color_pair(c_cfg["feedback"]) | curses.A_BOLD # Use feedback color (white) and make it BOLD
        nnl=[]
        for x,y,c,d in anim_s["music_notes"]:
            ny,ndf = y-NOTE_FLOAT_SPEED,d+NOTE_FLOAT_SPEED
            if ndf<NOTE_MAX_FLOAT_LINES and ny>=0:
                nnl.append((x,ny,c,ndf))
        anim_s["music_notes"]=nnl
        mn=int(a_w*MAX_NOTES_PER_WIDTH_UNIT)
        if random.random()<0.15 and len(anim_s["music_notes"])<mn and a_w>0 and a_h>0:
            anim_s["music_notes"].append((random.randint(0,a_w-1),a_h-1,random.randint(0,len(NOTE_CHARS)-1),0))
        for x,y,c,_ in anim_s["music_notes"]:
            if 0<=int(y)<a_h:
                _draw_char_safe(stdscr,y_s+int(y),x_s+x,NOTE_CHARS[c],lc)

def draw_ui(stdscr, sound_states, feedback_message, h, w, animation_state, color_cfg, help_active):
    stdscr.erase()
    current_instructions_area_h = len(HELP_LINES_TEXT) if help_active else DEFAULT_INSTRUCTIONS_AREA_H

    instructions_area_end_y = h - 2
    instructions_area_start_y = instructions_area_end_y - current_instructions_area_h + 1

    hline_above_instructions_y = instructions_area_start_y - 1
    track_info_end_y = hline_above_instructions_y -1
    track_info_start_y = track_info_end_y - TRACK_INFO_H +1
    hline_above_tracks_y = track_info_start_y - TRACK_INFO_HLINE_H
    title_y = 0
    anim_y_start = title_y + TITLE_H
    anim_y_end = hline_above_tracks_y -1
    actual_anim_height = max(0, anim_y_end - anim_y_start + 1)

    border_color = curses.color_pair(color_cfg["border"])
    stdscr.attron(border_color)
    try:
        stdscr.box()
    except curses.error:
        pass
    stdscr.attroff(border_color)

    title_actual_color = curses.color_pair(color_cfg["main_text"])|curses.A_BOLD
    if w > len(PLAYER_TITLE)+2 and title_y >= 0 and title_y < h:
        try:
            stdscr.addstr(title_y,(w-len(PLAYER_TITLE))//2,PLAYER_TITLE,title_actual_color)
        except curses.error:
            pass

    stdscr.attron(border_color)
    try:
        if hline_above_tracks_y > anim_y_end and hline_above_tracks_y < track_info_start_y and \
           hline_above_tracks_y > 0 and hline_above_tracks_y < h -1 and w > 2:
            stdscr.hline(hline_above_tracks_y,1,curses.ACS_HLINE,w-2)

        if hline_above_instructions_y > track_info_end_y and hline_above_instructions_y < instructions_area_start_y and \
           hline_above_instructions_y > 0 and hline_above_instructions_y < h - 1 and w > 2:
            stdscr.hline(hline_above_instructions_y,1,curses.ACS_HLINE,w-2)
    except curses.error:
        pass
    stdscr.attroff(border_color)

    if actual_anim_height >= MIN_ANIMATION_H and w > 2:
        update_and_draw_animations(stdscr,anim_y_start,actual_anim_height,1,w-2,sound_states,animation_state,color_cfg)

    if track_info_start_y <= track_info_end_y and track_info_start_y > anim_y_start-1 and track_info_start_y < h -1 :
        if track_info_start_y > 0:
             draw_track_info_line(stdscr,track_info_start_y,"Lofi",sound_states["lofi"],w,color_cfg["main_text"],color_cfg["error"])
        if track_info_start_y+1 > 0 and track_info_start_y+1 < h-1:
             draw_track_info_line(stdscr,track_info_start_y+1,"Rain",sound_states["rain"],w,color_cfg["main_text"],color_cfg["error"])
        if track_info_start_y+2 > 0 and track_info_start_y+2 < h-1:
             draw_track_info_line(stdscr,track_info_start_y+2,"Storm",sound_states["storm"],w,color_cfg["main_text"],color_cfg["error"])

    instr_color = curses.color_pair(color_cfg["main_text"])
    for i in range(current_instructions_area_h):
        y_line_to_clear = instructions_area_start_y + i
        if 0 < y_line_to_clear < h - 1 and w > 2 :
            try:
                stdscr.addstr(y_line_to_clear, 1, " " * (w - 2))
            except curses.error:
                pass

    if help_active:
        for i, line in enumerate(HELP_LINES_TEXT):
            if i < current_instructions_area_h:
                y_pos = instructions_area_start_y + i
                if 0 < y_pos < h -1 and y_pos <= instructions_area_end_y and w > len(line) + 2:
                    try:
                        stdscr.attron(instr_color)
                        stdscr.addstr(y_pos, max(1,(w - len(line)) // 2), line[:w-2])
                        stdscr.attroff(instr_color)
                    except curses.error:
                        pass
    else:
        main_instr_text = "[L/O/K]Lofi [R/E/D]Rain [S/T/G]Storm [H]Help [Q]Quit"
        preset_instr_text = "Presets: [1]Chill [2]Storm [3]LofiOnly [0]Silence"
        instr_y1 = instructions_area_start_y
        instr_y2 = instructions_area_start_y + 1
        feedback_line_y = instructions_area_start_y + 2

        if 0 < instr_y1 < h -1 and instr_y1 <= instructions_area_end_y and w > len(main_instr_text)+2:
            try:
                stdscr.attron(instr_color)
                stdscr.addstr(instr_y1,max(1,(w-len(main_instr_text))//2),main_instr_text[:w-2])
                stdscr.attroff(instr_color)
            except curses.error:
                pass
        if 0 < instr_y2 < h -1 and instr_y2 <= instructions_area_end_y and w > len(preset_instr_text)+2:
            try:
                stdscr.attron(instr_color)
                stdscr.addstr(instr_y2,max(1,(w-len(preset_instr_text))//2),preset_instr_text[:w-2])
                stdscr.attroff(instr_color)
            except curses.error:
                pass
        if 0 < feedback_line_y < h -1 and feedback_line_y <= instructions_area_end_y and w > 3:
            feedback_actual_color = curses.color_pair(color_cfg["feedback"])|curses.A_BOLD
            try:
                stdscr.attron(feedback_actual_color)
                stdscr.addstr(feedback_line_y, 2, feedback_message.ljust(w-3)[:w-3])
                stdscr.attroff(feedback_actual_color)
            except curses.error:
                pass

def draw_minimal_ui(stdscr, feedback_message, h, w, color_cfg):
    stdscr.erase()
    line_idx = 0
    try:
        title = PLAYER_TITLE
        if h > line_idx and w > len(title)+2:
            stdscr.attron(curses.color_pair(color_cfg["main_text"])|curses.A_BOLD)
            stdscr.addstr(line_idx,(w-len(title))//2,title)
            stdscr.attroff(curses.color_pair(color_cfg["main_text"])|curses.A_BOLD)
            line_idx+=1
        if h > line_idx and w > 2:
            stdscr.attron(curses.color_pair(color_cfg["border"]))
            stdscr.hline(line_idx,1,curses.ACS_HLINE,w-2)
            stdscr.attroff(curses.color_pair(color_cfg["border"]))
            line_idx+=1
    except curses.error:
        pass
    fb_y=h-1
    can_fb=False
    try:
        if fb_y >= line_idx and w > 2:
            stdscr.attron(curses.color_pair(color_cfg["feedback"])|curses.A_BOLD)
            stdscr.addstr(fb_y,1,feedback_message.ljust(w-2)[:w-2])
            stdscr.attroff(curses.color_pair(color_cfg["feedback"])|curses.A_BOLD)
            can_fb=True
    except curses.error:
        pass
    instr_sy=line_idx; instr_ey=fb_y-1 if can_fb else h-1
    try:
        if instr_sy <= instr_ey:
            instr_texts = ["[LOK]Lofi [RED]Rain [STG]Storm [H]Help [Q]Quit", "Presets: [1][2][3][0]"]
            total_ih=len(instr_texts); avail_ih=instr_ey-instr_sy+1;
            sdy = instr_sy + max(0, (avail_ih - total_ih) // 2)

            for i,txt in enumerate(instr_texts):
                if i>=avail_ih: break
                cur_y=sdy+i
                if cur_y < instr_sy or cur_y > instr_ey or cur_y >= h: continue

                stxt=txt
                if "Presets" in txt and w<len(txt)+4:stxt="Presets(1-3,0)"
                elif w<len(txt)+4:stxt="Keys:LOK RED STG H Q"
                chosen=txt if w>=len(txt)+4 else stxt

                if w > len(chosen)+2 :
                    stdscr.attron(curses.color_pair(color_cfg["main_text"]))
                    ixp=max(1,(w-len(chosen))//2)
                    stdscr.addstr(cur_y,ixp,chosen[:w-ixp-1])
                    stdscr.attroff(curses.color_pair(color_cfg["main_text"]))
    except curses.error:
        pass

def main_curses(stdscr):
    curses.curs_set(0); stdscr.nodelay(True); stdscr.timeout(100)
    curses.start_color(); curses.use_default_colors()

    ccfg={"main_text":1,"border":2,"error":3,"feedback":4, "rain":5,"lightning":6}

    r,g,b=int(97/255*1000),int(52/255*1000),int(235/255*1000); fb_extra=""
    if curses.can_change_color() and curses.COLORS>=16:
        try:
            curses.init_color(COLOR_PURPLE_CUSTOM_ID,r,g,b)
            curses.init_pair(ccfg["main_text"],COLOR_PURPLE_CUSTOM_ID,-1)
        except curses.error:
            curses.init_pair(ccfg["main_text"],curses.COLOR_MAGENTA,-1)
            fb_extra=" (Custom color fail)"
    else:
        curses.init_pair(ccfg["main_text"],curses.COLOR_MAGENTA,-1)
        fb_extra=" (No custom purple)" if not curses.can_change_color() else f" ({curses.COLORS} colors only)"

    curses.init_pair(ccfg["border"],curses.COLOR_BLUE,-1)
    curses.init_pair(ccfg["error"],curses.COLOR_RED,-1)
    curses.init_pair(ccfg["feedback"],curses.COLOR_WHITE,-1)
    curses.init_pair(ccfg["rain"],curses.COLOR_CYAN,-1)
    curses.init_pair(ccfg["lightning"],curses.COLOR_YELLOW,-1)


    mpv_procs={}
    s_states={ "lofi":{"playing":True,"volume":50,"socket":get_socket_path("lofi"),"media":LOFI_STREAM_URL},
               "rain":{"playing":False,"volume":50,"socket":get_socket_path("rain"),"media":RAIN_SOUND_FILE},
               "storm":{"playing":False,"volume":50,"socket":get_socket_path("storm"),"media":STORM_SOUND_FILE}}
    for k_init in s_states:
        s_states[k_init].update({"is_running":False,"_file_not_found":False,"_mpv_not_found":False})
        if k_init == "lofi":
             s_states[k_init]["_no_internet"] = False

    anim_s={"rain_drops":[],"lightning_bolt":None,"music_notes":[]}
    fb_msg="Welcome!"+fb_extra; fb_timer=30; help_active=False; help_timer=0

    for ks_init in ["rain","storm"]:
        if not os.path.exists(s_states[ks_init]["media"]):
            try:
                with open(s_states[ks_init]["media"],'a') as f:
                    if os.path.getsize(s_states[ks_init]["media"]) == 0:
                         fb_msg += f" {ks_init.capitalize()} file created."
            except OSError:
                fb_msg += f" Err creating {ks_init} file."
                pass

    for st_k_init_mpv, state_vals in s_states.items():
        if state_vals["playing"]:
            initial_fb = set_sound_state(st_k_init_mpv, True, state_vals["volume"], s_states, mpv_procs)
            if "failed" in initial_fb or "No internet" in initial_fb or "not found" in initial_fb :
                fb_msg = initial_fb
            elif fb_msg.startswith("Welcome"):
                fb_msg = initial_fb


    while True:
        h,w=stdscr.getmaxyx(); key=stdscr.getch()

        if key==curses.KEY_RESIZE:
            stdscr.clear()

        current_min_instr_h = len(HELP_LINES_TEXT) if help_active else DEFAULT_INSTRUCTIONS_AREA_H
        min_h_for_full_ui = (TITLE_H + MIN_ANIMATION_H + TRACK_INFO_HLINE_H +
                             TRACK_INFO_H + 1 +
                             current_min_instr_h)


        if key!=-1 and key!=curses.KEY_RESIZE:
            if not help_active:
                 fb_timer=30
            ck=chr(key) if 0<=key<256 else ''

            if key==ord('q'):
                fb_msg="Quitting...";
                stdscr.erase()
                if h<min_h_for_full_ui or w<MIN_FULL_UI_W:draw_minimal_ui(stdscr,fb_msg,h,w,ccfg)
                else:draw_ui(stdscr,s_states,fb_msg,h,w,anim_s,ccfg,help_active)
                stdscr.refresh();time.sleep(0.5);break

            if key==ord('h'):
                help_active = not help_active
                if help_active: help_timer = HELP_DISPLAY_DURATION_FRAMES; fb_msg = ""
                else: help_timer = 0; fb_msg = "Help dismissed."; fb_timer = 20
            elif help_active and key != ord('h'):
                help_active = False; help_timer = 0; fb_msg = "Help dismissed by key."; fb_timer = 20

            if not help_active:
                actions={'l':lambda:toggle_play_pause("lofi",s_states, mpv_procs),
                         'o':lambda:adjust_volume("lofi",5,s_states),
                         'k':lambda:adjust_volume("lofi",-5,s_states),
                         'r':lambda:toggle_play_pause("rain",s_states, mpv_procs),
                         'e':lambda:adjust_volume("rain",5,s_states),
                         'd':lambda:adjust_volume("rain",-5,s_states),
                         's':lambda:toggle_play_pause("storm",s_states, mpv_procs),
                         't':lambda:adjust_volume("storm",5,s_states),
                         'g':lambda:adjust_volume("storm",-5,s_states)}
                if ck in SOUND_PRESETS:
                    act=lambda c=ck:apply_preset(c,s_states,mpv_procs)
                else:
                    act=actions.get(ck.lower())

                if act: fb_msg=act() if callable(act) else act
                elif ck and fb_timer > 0 :
                    fb_timer = 1

        if help_active and help_timer > 0:
            help_timer -= 1
            if help_timer == 0: help_active = False; fb_msg = fb_msg or "Help timed out."; fb_timer = 20
        if not help_active and fb_timer > 0:
            fb_timer -= 1
            if fb_timer == 0: fb_msg = ""

        for stk_loop in list(s_states.keys()):
            p_loop=mpv_procs.get(stk_loop)
            if p_loop and p_loop.poll() is not None:
                current_state = s_states[stk_loop]
                was_intended_to_play = current_state["playing"]
                was_actually_running = current_state["is_running"]

                current_state.update({"is_running":False,"playing":False})

                if stk_loop == "lofi" and was_intended_to_play and was_actually_running:
                    if not check_internet_connection(timeout=1):
                        current_state["_no_internet"] = True

                if os.path.exists(current_state["socket"]):
                    try: os.remove(current_state["socket"])
                    except OSError: pass
                if stk_loop in mpv_procs: del mpv_procs[stk_loop]


        if h<min_h_for_full_ui or w<MIN_FULL_UI_W:
            draw_minimal_ui(stdscr,fb_msg,h,w,ccfg)
        else:
            draw_ui(stdscr,s_states,fb_msg,h,w,anim_s,ccfg,help_active)
        stdscr.refresh()

    for sk_cleanup,p_cleanup in mpv_procs.items():
        if p_cleanup and p_cleanup.poll() is None:
            if os.path.exists(s_states[sk_cleanup]["socket"]):
                send_mpv_command(s_states[sk_cleanup]["socket"],{"command":["quit"]})
            try:
                p_cleanup.wait(0.5)
            except subprocess.TimeoutExpired:
                if p_cleanup.poll() is None:
                    p_cleanup.kill()
                    p_cleanup.wait(0.2)
    for stk_final_cleanup in s_states:
        if os.path.exists(s_states[stk_final_cleanup]["socket"]):
            try: os.remove(s_states[stk_final_cleanup]["socket"])
            except OSError: pass

if __name__=="__main__":
    if not os.path.exists(SOCKET_DIR):
        try: os.makedirs(SOCKET_DIR,exist_ok=True)
        except OSError as e: print(f"Error creating socket directory {SOCKET_DIR}:{e}");sys.exit(1)
    try:
        curses.wrapper(main_curses)
    except curses.error as e:
        print(f"Curses error: {e}")
        print("If on Windows, ensure you have 'windows-curses' installed (pip install windows-curses).")
        print("Ensure your terminal supports colors and is properly configured (e.g., TERM environment variable).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"{PLAYER_TITLE} closed.")
