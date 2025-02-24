import hou
import requests
from datetime import datetime, timedelta
import os
import glob
import imageio
import numpy as np
from PIL import Image
import json
import traceback
from PySide2 import QtWidgets, QtCore

CONFIG_FILE = os.path.join(hou.getenv("HOUDINI_USER_PREF_DIR"), "telegram_config.json")
NOTIFICATIONS_ENABLED = False
SESSION_RENDERS = {}
CURRENT_RENDERS = {}
CALLBACK_REGISTRY = set()
SHELF_TOOL_CREATED = False

def load_config():
    """Load or create the Telegram configuration file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    else:
        bot_token = hou.ui.readInput("Enter your Telegram BOT_TOKEN")[1]
        chat_id = hou.ui.readInput("Enter your Telegram CHAT_ID (separate multiple IDs with commas)")[1]
        chat_ids = [cid.strip() for cid in chat_id.split(",")]
        config = {
            "BOT_TOKEN": bot_token,
            "CHAT_IDS": chat_ids
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print(f"Configuración guardada en: {CONFIG_FILE}")
        ask_to_create_shelf_tool()
    return config

config = load_config()
BOT_TOKEN = config["BOT_TOKEN"]
CHAT_ID = config.get("CHAT_IDS", config.get("CHAT_ID"))


def get_shelves_path():
    """Obtiene la ruta de los estantes (shelves) de manera procedural."""
    user_pref_dir = hou.getenv("HOUDINI_USER_PREF_DIR")
    toolbar_path = os.path.join(user_pref_dir, "toolbar")
    
    if os.path.exists(toolbar_path):
        return toolbar_path
    else:
        print(f"La carpeta 'toolbar' no existe en: {toolbar_path}")
        # Intentar crear el directorio si no existe
        try:
            os.makedirs(toolbar_path)
            print(f"Creado directorio de toolbar en: {toolbar_path}")
            return toolbar_path
        except Exception as e:
            print(f"Error creando directorio toolbar: {str(e)}")
            return None

def get_shelves():
    """
    Obtiene una lista de los nombres de los estantes existentes.
    Returns a list of shelf names, handling potential errors gracefully.
    """
    try:
        # Get shelves dictionary directly without accessing settings
        shelves_dict = hou.shelves.shelves()
        return list(shelves_dict.keys())
    except Exception as e:
        print(f"Error retrieving shelves: {str(e)}")
        return []

def create_shelf_tool(shelf_name, tool_name="telegram_notifications", 
                     tool_label="Telegram Notifications", tool_script=None, tool_icon="MESSAGE"):
    """
    Creates a tool in a specified shelf using the Houdini API.
    Added error handling and validation.
    """
    try:
        # Validate inputs
        if not shelf_name or not tool_name:
            print("Invalid shelf name or tool name")
            return False
            
        # Format tool name
        tool_name = str(tool_name).replace(" ", "_")
        
        # Get shelves dictionary
        shelves = hou.shelves.shelves()
        shelf = shelves.get(shelf_name)
        
        if not shelf:
            print(f"Shelf '{shelf_name}' not found")
            return False
        
        # Create default script if none provided
        if tool_script is None:
            tool_script = """
import telegram_notifications
telegram_notifications.create_ui()
            """
        
        # Create the tool
        try:
            tool = hou.shelves.newTool(
                name=tool_name,
                label=tool_label,
                script=tool_script,
                icon=tool_icon
            )
        except Exception as e:
            print(f"Error creating tool: {str(e)}")
            return False
            
        # Add tool to shelf
        try:
            tools = list(shelf.tools())
            tools.append(tool)
            shelf.setTools(tools)
            
            # Los cambios se guardan automáticamente al modificar el shelf
            # No necesitamos llamar a saveShelves() explícitamente
            
        except Exception as e:
            print(f"Error adding tool to shelf: {str(e)}")
            return False
            
        print(f"Successfully created tool '{tool_label}' in shelf '{shelf_name}'")
        return True
        
    except Exception as e:
        print(f"Error in create_shelf_tool: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def ask_to_create_shelf_tool():
    """
    Prompts user to create a shelf tool and handles the creation process.
    Added robust error handling and user feedback.
    """
    try:
        result = hou.ui.displayMessage(
            "Would you like to create a shelf tool for Telegram notifications?",
            buttons=("Yes", "No"),
            default_choice=0,
            close_choice=1,
            title="Create Shelf Tool"
        )
        
        if result == 0:  # User chose "Yes"
            # Get available shelves
            available_shelves = get_shelves()
            
            if not available_shelves:
                print("No shelves available")
                return
                
            # Show selection dialog
            selected = hou.ui.selectFromList(
                available_shelves,
                title="Select Shelf",
                message="Choose a shelf to add the tool to:",
                default_choices=(0,),
                clear_on_cancel=True
            )
            
            if selected:
                shelf_name = available_shelves[selected[0]]
                script_content = """
import telegram_notifications
telegram_notifications.create_ui()
                """
                
                success = create_shelf_tool(
                    shelf_name=shelf_name,
                    tool_name="telegram_notifier",
                    tool_label="Telegram Notifications",
                    tool_script=script_content,
                    tool_icon="MESSAGE"
                )
                
                if success:
                    print(f"Tool successfully created in shelf: {shelf_name}")
                else:
                    print("Failed to create tool")
            else:
                print("Tool creation cancelled")
                
    except Exception as e:
        print(f"Error in ask_to_create_shelf_tool: {str(e)}")
        traceback.print_exc()

def get_progress_bar(progress):
    bar_length = 10
    filled = int(round(bar_length * progress))
    return "🟩" * filled + "⬜" * (bar_length - filled)

def send_telegram_message(message):
    if isinstance(CHAT_ID, list):
        for chat_id in CHAT_ID:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            try:
                response = requests.post(url, data=data)
                if response.ok:
                    return response.json()["result"]["message_id"]
            except Exception as e:
                ui.log_message(f"Error sending message to chat {chat_id}: {str(e)}")
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, data=data)
            if response.ok:
                return response.json()["result"]["message_id"]
        except Exception as e:
            ui.log_message(f"Error sending message: {str(e)}")
    return None

def convert_frame_to_rgb(frame_path):
    try:
        with Image.open(frame_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return np.array(img)
    except Exception as e:
        ui.log_message(f"Error converting frame {frame_path}: {str(e)}")
        return None

def resize_frame(frame, max_size=(800, 800)):
    img = Image.fromarray(frame)
    w, h = img.size
    if h > max_size[1] or w > max_size[0]:
        ratio = min(max_size[0] / w, max_size[1] / h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.ANTIALIAS)
    return np.array(img)

def should_update_progress(state):
    now = datetime.now()
    time_since_update = (now - state['last_update_time']).total_seconds()
    if time_since_update >= state['update_interval']:
        state['last_update_time'] = now
        return True
    return False

def clear_duplicates():
    for node in hou.node('/').allSubChildren():
        if is_render_node(node):
            callbacks = node.eventCallbacks()
            unique_callbacks = list(set(callbacks))
            if len(callbacks) != len(unique_callbacks):
                node.removeAllEventCallbacks()
                for callback in unique_callbacks:
                    node.addEventCallback((callback,))

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def send_telegram_animation(node, frames_path_pattern):
    try:
        frames = sorted(glob.glob(frames_path_pattern))
        if not frames:
            ui.log_message(f"No frames found matching pattern: {frames_path_pattern}")
            return False

        if len(frames) == 1:
            frame_path = frames[0]
            ui.log_message(f"Processing single frame: {frame_path}")
            frame_rgb = convert_frame_to_rgb(frame_path)
            if frame_rgb is None:
                ui.log_message(f"Failed to convert frame {frame_path} to RGB")
                return False
            frame_resized = resize_frame(frame_rgb)
            temp_png = "temp_render_preview.png"
            Image.fromarray(frame_resized).save(temp_png)
            ui.log_message("Sending single frame to Telegram...")
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(temp_png, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    "chat_id": CHAT_ID,
                    "caption": f"🎬 Single frame preview for {get_node_name(node)}"
                }
                response = requests.post(url, data=data, files=files)
                if not response.ok:
                    ui.log_message(f"Failed to send single frame: {response.text}")
                    return False
            os.remove(temp_png)
            return True
        else:
            temp_gif = "temp_render_preview.gif"
            if len(frames) > 30:
                sample_indices = list(range(0, 10))
                middle_frames = list(range(10, len(frames)-10, (len(frames)-20)//10))
                sample_indices.extend(middle_frames)
                sample_indices.extend(list(range(len(frames)-10, len(frames))))
                frames = [frames[i] for i in sorted(set(sample_indices))]
            ui.log_message(f"Processing {len(frames)} frames for preview...")
            images = []
            for frame_path in frames:
                try:
                    frame_rgb = convert_frame_to_rgb(frame_path)
                    if frame_rgb is None:
                        continue
                    frame_resized = resize_frame(frame_rgb)
                    images.append(Image.fromarray(frame_resized))
                except Exception as e:
                    ui.log_message(f"Error processing frame {frame_path}: {str(e)}")
                    continue
            if images:
                ui.log_message("Creating GIF...")
                first_image = images[0]
                first_image.save(
                    temp_gif,
                    save_all=True,
                    append_images=images[1:],
                    optimize=False,
                    duration=100,
                    loop=0
                )
                ui.log_message("Sending animation to Telegram...")
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAnimation"
                with open(temp_gif, 'rb') as animation:
                    files = {'animation': animation}
                    data = {
                        "chat_id": CHAT_ID,
                        "caption": f"🎬 Animation preview for {get_node_name(node)}"
                    }
                    response = requests.post(url, data=data, files=files)
                    if not response.ok:
                        ui.log_message(f"Failed to send animation: {response.text}")
                os.remove(temp_gif)
                for img in images:
                    img.close()
                return True
            else:
                ui.log_message("No frames were successfully processed")
                return False
    except Exception as e:
        ui.log_message(f"Error creating/sending animation: {str(e)}")
        if os.path.exists(temp_gif):
            os.remove(temp_gif)
        return False

def get_render_engine(node):
    try:
        type_name = node.type().name()
        if type_name == 'ifd':
            return "Mantra"
        if type_name == 'usdrender_rop':
            return "Karma"
        return type_name
    except:
        return "Unknown"

def get_node_name(node):
    try:
        return node.name()
    except:
        return node.path()

def get_sequence_range(node):
    try:
        if not node.parm('trange'):
            return (1, 1)
        if node.parm('trange').eval() == 0:
            return (1, 1)
        start = node.parm('f1').eval()
        end = node.parm('f2').eval()
        return (start, end)
    except:
        return (1, 1)

def is_render_node(node):
    try:
        type_name = node.type().name()
        return type_name in ['ifd', 'usdrender_rop']
    except:
        return False

def update_render_stats(node_path, render_time, frame_count=1):
    if node_path not in SESSION_RENDERS:
        SESSION_RENDERS[node_path] = {
            'times': [],
            'total_renders': 0,
            'frames_rendered': 0,
            'total_time': 0
        }
    SESSION_RENDERS[node_path]['times'].append(render_time)
    SESSION_RENDERS[node_path]['total_renders'] += 1
    SESSION_RENDERS[node_path]['frames_rendered'] += frame_count
    SESSION_RENDERS[node_path]['total_time'] += render_time
    if len(SESSION_RENDERS[node_path]['times']) > 10:
        SESSION_RENDERS[node_path]['times'].pop(0)

def get_render_stats(node_path):
    if node_path not in SESSION_RENDERS:
        return None
    stats = SESSION_RENDERS[node_path]
    if not stats['times']:
        return None
    total_frames = stats['frames_rendered']
    total_time = stats['total_time']
    avg_per_frame = total_time / total_frames if total_frames > 0 else 0
    return {
        'average': format_time(avg_per_frame),
        'total_renders': stats['total_renders'],
        'last_render': format_time(stats['times'][-1]) if stats['times'] else "N/A"
    }

def initialize_render_state(node):
    start, end = get_sequence_range(node)
    frame_count = int(end - start + 1)
    return {
        'start_time': datetime.now(),
        'message_id': None,
        'completed_frames': set(),
        'total_frames': frame_count,
        'start_frame': int(start),
        'end_frame': int(end),
        'last_update_time': datetime.now(),
        'update_interval': 2.0
    }

def on_render_event(node, event_type, frame_time):
    global NOTIFICATIONS_ENABLED
    if not NOTIFICATIONS_ENABLED:
        return
    try:
        node_path = node.path()
        if event_type == hou.ropRenderEventType.PreRender:
            if node_path in CURRENT_RENDERS:
                return
            CURRENT_RENDERS[node_path] = initialize_render_state(node)
            state = CURRENT_RENDERS[node_path]
            message = (
                f"🎬 Render Started!\n"
                f"🎨 Engine: {get_render_engine(node)}\n"
                f"📁 Node: {get_node_name(node)}\n"
                f"🎯 Frames: {state['start_frame']} to {state['end_frame']} ({state['total_frames']} frames)\n"
                f"⏱️ Frame Progress: 0/{state['total_frames']} (0%)"
            )
            msg_id = send_telegram_message(message)
            if msg_id:
                CURRENT_RENDERS[node_path]['message_id'] = msg_id
        elif event_type == hou.ropRenderEventType.PostFrame:
            if node_path not in CURRENT_RENDERS:
                return
            state = CURRENT_RENDERS[node_path]
            state['completed_frames'].add(float(frame_time))
            if should_update_progress(state):
                duration = (datetime.now() - state['start_time']).total_seconds()
                frames_done = len(state['completed_frames'])
                total_frames = state['total_frames']
                avg_time_per_frame = duration / frames_done if frames_done > 0 else 0
                estimated_total = avg_time_per_frame * total_frames
                time_remaining = max(0, estimated_total - duration)
                progress_percent = (frames_done / total_frames) * 100
                completion_time = datetime.now() + timedelta(seconds=time_remaining)
                formatted_completion_time = completion_time.strftime("%H:%M:%S")
                progress_bar = get_progress_bar(frames_done / total_frames)
                message = (
                    f"🎬 Render In Progress\n"
                    f"🎨 Engine: {get_render_engine(node)}\n"
                    f"📁 Node: {get_node_name(node)}\n"
                    f"🎯 Progress: {frames_done}/{total_frames} frames ({progress_percent:.1f}%)\n"
                    f"📊 {progress_bar}\n"
                    f"⏱️ Time elapsed: {format_time(duration)}\n"
                    f"⏳ Estimated remaining: {format_time(time_remaining)}\n"
                    f"🏁 Estimated completion: {formatted_completion_time}\n"
                    f"🔄 Average per frame: {format_time(avg_time_per_frame)}"
                )
                if state['message_id']:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
                    data = {
                        "chat_id": CHAT_ID,
                        "message_id": state['message_id'],
                        "text": message,
                        "parse_mode": "HTML"
                    }
                    try:
                        requests.post(url, data=data)
                    except Exception as e:
                        ui.log_message(f"Error updating frame progress: {str(e)}")
        elif event_type == hou.ropRenderEventType.PostRender:
            if node_path not in CURRENT_RENDERS:
                return
            state = CURRENT_RENDERS[node_path]
            render_duration = (datetime.now() - state['start_time']).total_seconds()
            frames_completed = len(state['completed_frames'])
            expected_frames = state['total_frames']
            if 0 < frames_completed < expected_frames:
                error_message = (
                    f"⏹️ Render Interrupted!\n"
                    f"🎨 Engine: {get_render_engine(node)}\n"
                    f"📁 Node: {get_node_name(node)}\n"
                    f"🎯 Progress when stopped: {frames_completed}/{expected_frames} frames\n"
                    f"📊 Completion: {(frames_completed/expected_frames*100):.1f}%\n"
                    f"⏱️ Time elapsed: {format_time(render_duration)}\n"
                    f"⚡ Last frame completed: {max(state['completed_frames']) if state['completed_frames'] else 'None'}\n"
                    f"📄 **Possible Causes:**\n"
                    f"- The render was manually interrupted.\n"
                    f"- There was an error in the render node."
                )
                if state['message_id']:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
                    data = {
                        "chat_id": CHAT_ID,
                        "message_id": state['message_id'],
                        "text": error_message,
                        "parse_mode": "HTML"
                    }
                    try:
                        requests.post(url, data=data)
                    except:
                        send_telegram_message(error_message)
            elif frames_completed == expected_frames:
                update_render_stats(node_path, render_duration, frames_completed)
                stats = get_render_stats(node_path)
                try:
                    if node.type().name() == 'ifd':
                        output_path = node.parm('vm_picture').eval()
                    elif node.type().name() == 'usdrender_rop':
                        referenced_nodes_rop = node.references()
                        for ref in referenced_nodes_rop:
                            if ref != node:
                                refNode = ref
                        output_path = refNode.parm('picture').eval()
                    output_dir = os.path.dirname(output_path)
                    file_base = os.path.basename(output_path)
                    name_parts = os.path.splitext(file_base)
                    base_pattern = os.path.join(output_dir, f"{name_parts[0].rsplit('.', 1)[0]}.*{name_parts[1]}")
                    ui.log_message(f"Searching for frames with pattern: {base_pattern}")
                    animation_sent = send_telegram_animation(node, base_pattern)
                    if animation_sent:
                        ui.log_message("Animation preview sent successfully!")
                except Exception as e:
                    ui.log_message(f"Could not generate animation preview: {str(e)}")
                message = (
                    f"✅ Render Complete!\n"
                    f"🎨 Engine: {get_render_engine(node)}\n"
                    f"📁 Node: {get_node_name(node)}\n"
                    f"🎯 Frames: {state['start_frame']} to {state['end_frame']} ({frames_completed} frames)\n"
                    f"⏱️ Total Duration: {format_time(render_duration)}\n\n"
                    f"📊 Statistics:\n"
                    f"Average time per frame: {stats['average']}\n"
                    f"Total frames rendered: {stats['total_renders']}"
                )
                if state['message_id']:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
                    data = {
                        "chat_id": CHAT_ID,
                        "message_id": state['message_id'],
                        "text": message,
                        "parse_mode": "HTML"
                    }
                    try:
                        requests.post(url, data=data)
                    except:
                        send_telegram_message(message)
                else:
                    send_telegram_message(message)
                completion_message = (
                    f"🔔 RENDER FINISHED!\n\n"
                    f"📁 {get_node_name(node)} is done rendering\n"
                    f"⏱️ Total time: {format_time(render_duration)}\n"
                    f"🎯 Frames completed: {frames_completed}/{state['total_frames']}"
                )
                send_telegram_message(completion_message)
            else:
                error_message = (
                    f"❌ RENDER FAILED!\n"
                    f"🎨 Engine: {get_render_engine(node)}\n"
                    f"📁 Node: {get_node_name(node)}\n"
                    f"⚠️ No frames were completed\n"
                    f"⏱️ Time elapsed: {format_time(render_duration)}\n"
                    f"📄 **Possible Causes:**\n"
                    f"- The render was manually interrupted.\n"
                    f"- There was an error in the render node.\n"
                    f"- The script failed to detect completed frames."
                )
                if state['message_id']:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
                    data = {
                        "chat_id": CHAT_ID,
                        "message_id": state['message_id'],
                        "text": error_message,
                        "parse_mode": "HTML"
                    }
                    try:
                        requests.post(url, data=data)
                    except:
                        send_telegram_message(error_message)
                else:
                    send_telegram_message(error_message)
            del CURRENT_RENDERS[node_path]
    except Exception as e:
        error_message = (
            f"🚨 **Render Failed - Error Details**\n"
            f"📁 Node: {get_node_name(node)}\n"
            f"⚠️ Error Type: {type(e).__name__}\n"
            f"📄 **Error Message:**\n"
            f"<pre>{str(e)}</pre>\n"
            f"📄 **Traceback:**\n"
            f"<pre>{traceback.format_exc()}</pre>\n"
            f"📄 **Possible Causes:**\n"
            f"- The render was manually interrupted.\n"
            f"- There was an error in the render node.\n"
            f"- The script failed to detect completed frames."
        )
        send_telegram_message(error_message)
        if node.path() in CURRENT_RENDERS:
            del CURRENT_RENDERS[node.path()]

def remove_all_callbacks():
    global CALLBACK_REGISTRY
    for node in hou.node('/').allSubChildren():
        if is_render_node(node):
            try:
                node.removeAllEventCallbacks()
            except Exception as e:
                ui.log_message(f"Error removing callbacks from {node.path()}: {str(e)}")
    CALLBACK_REGISTRY.clear()
    ui.update_callbacks_list()

def setup_render_callbacks():
    global CALLBACK_REGISTRY
    remove_all_callbacks()
    for node in hou.node('/').allSubChildren():
        if is_render_node(node):
            try:
                node_path = node.path()
                if node_path not in CALLBACK_REGISTRY:
                    node.addRenderEventCallback(on_render_event)
                    CALLBACK_REGISTRY.add(node_path)
            except Exception as e:
                ui.log_message(f"Error adding callback to {node_path}: {str(e)}")
    ui.update_callbacks_list()

def test_telegram_connection():
    message = "🔄 Test message from Houdini - If you see this, the notification system is working!"
    if send_telegram_message(message):
        ui.log_message("Test message sent successfully! Check your Telegram.")
    else:
        ui.log_message("Failed to send test message. Check your BOT_TOKEN and CHAT_ID.")

# Variable global para almacenar la instancia de la UI
UI_INSTANCE = None

def create_ui():
    """
    Crea o muestra la interfaz de usuario.
    Si ya existe una instancia, la trae al frente.
    Si no existe, crea una nueva.
    """
    global UI_INSTANCE

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    # Si ya existe una instancia de la UI, la traemos al frente
    if UI_INSTANCE is not None:
        UI_INSTANCE.show()
        UI_INSTANCE.raise_()
        return UI_INSTANCE

    # Si no existe, creamos una nueva instancia
    UI_INSTANCE = TelegramNotificationsUI()
    UI_INSTANCE.show()
    return UI_INSTANCE

class TelegramNotificationsUI(QtWidgets.QWidget):
    def __init__(self):
        super(TelegramNotificationsUI, self).__init__()
        self.setWindowTitle("Telegram Render Notifications")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.init_ui()

    # Aquí va la clase CustomInputDialog (dentro de TelegramNotificationsUI)
    class CustomInputDialog(QtWidgets.QDialog):
        def __init__(self, title, label, parent=None):
            super().__init__(parent)
            
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
            self.setWindowTitle(title)
            self.setMinimumWidth(400)
            
            # Layout principal
            layout = QtWidgets.QVBoxLayout(self)
            
            # Layout superior para el botón de ayuda
            top_layout = QtWidgets.QHBoxLayout()
            
            # Espaciador para empujar el botón de ayuda a la derecha
            spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            top_layout.addItem(spacer)
            
            # Botón de ayuda
            help_button = QtWidgets.QPushButton("❓", self)
            help_button.setFixedSize(30, 30)
            help_button.setStyleSheet("font-size: 15px;")
            help_button.clicked.connect(self.show_help)
            top_layout.addWidget(help_button)
            
            layout.addLayout(top_layout)
            
            # Label e input
            layout.addWidget(QtWidgets.QLabel(label))
            self.input_field = QtWidgets.QLineEdit(self)
            layout.addWidget(self.input_field)
            
            # Botones
            button_box = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                self
            )
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)

        def show_help(self):
            help_text = (
                "📝 <b>How to Get Telegram BOT_TOKEN and CHAT_ID</b><br><br>"
                "1. <b>Create a Telegram Bot:</b><br>"
                "   - Open Telegram and search for the <b>BotFather</b>.<br>"
                "   - Start a chat with BotFather and use the <b>/newbot</b> command.<br>"
                "   - Follow the instructions to create a new bot.<br>"
                "   - At the end, BotFather will give you a <b>BOT_TOKEN</b>.<br><br>"
                "2. <b>Get Your CHAT_ID:</b><br>"
                "   <b>Option 1: Using Raw Data Bot</b><br>"
                "   - Open Telegram and search for the <b>Raw Data Bot</b>.<br>"
                "   - Start a chat with the bot and send any message.<br>"
                "   - The bot will reply with your <b>CHAT_ID</b>.<br><br>"
                "   <b>Option 2: Using getUpdates API</b><br>"
                "   - Open Telegram and search for the bot you just created.<br>"
                "   - Start a chat with the bot and send any message.<br>"
                "   - Go to <b>https://api.telegram.org/bot&lt;YOUR_BOT_TOKEN&gt;/getUpdates</b>.<br>"
                "   - Look for the <b>chat.id</b> field in the response.<br><br>"
                "3. <b>Configure the Script:</b><br>"
                "   - Enter the <b>BOT_TOKEN</b> and <b>CHAT_ID</b> in the configuration dialog.<br>"
                "   - Separate multiple CHAT_IDs with commas if needed.<br><br>"
                "🔗 <b>For more details, visit:</b><br>"
                "<a href='https://core.telegram.org/bots#creating-a-new-bot'>Telegram Bot Documentation</a>"
            )
            help_dialog = QtWidgets.QMessageBox(self)
            help_dialog.setWindowTitle("Help")
            help_dialog.setTextFormat(QtCore.Qt.RichText)
            help_dialog.setText(help_text)
            help_dialog.exec_()

        def get_input(self):
            return self.input_field.text()

    def init_ui(self):
        """
        Inicializa la interfaz de usuario.
        """
        main_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()

        # Layout de cuadrícula para los botones superiores
        buttons_grid = QtWidgets.QGridLayout()

        # Botón de configuración (fila 0, columna 0)
        self.config_button = QtWidgets.QPushButton("Configure Telegram Bot")
        self.config_button.clicked.connect(self.configure_telegram_bot)
        self.config_button.setStyleSheet("")
        buttons_grid.addWidget(self.config_button, 0, 0)

        # Botón para crear la Shelf Tool (fila 0, columna 1)
        self.shelf_tool_button = QtWidgets.QPushButton("Create Shelf Tool")
        self.shelf_tool_button.clicked.connect(self.create_shelf_tool)  # Conectar el botón al método
        self.shelf_tool_button.setStyleSheet("")
        buttons_grid.addWidget(self.shelf_tool_button, 0, 1)

        # Botón de Help (fila 0 y 1, columna 2, ocupa 2 filas)
        self.help_button = QtWidgets.QPushButton("❓")
        self.help_button.setFixedSize(50, 50)  # Tamaño cuadrado
        self.help_button.clicked.connect(self.show_help)
        self.help_button.setStyleSheet("font-size: 20px;")  # Tamaño del emoji
        buttons_grid.addWidget(self.help_button, 0, 2, 2, 1)  # Ocupa 2 filas y 1 columna

        # Botón de prueba de conexión (fila 1, columna 0)
        self.test_button = QtWidgets.QPushButton("Test Telegram Connection")
        self.test_button.clicked.connect(self.test_telegram_connection)
        self.test_button.setStyleSheet("")
        buttons_grid.addWidget(self.test_button, 1, 0)

        # Botón para habilitar/deshabilitar notificaciones (fila 1, columna 1)
        self.toggle_button = QtWidgets.QPushButton("Enable Notifications")
        self.toggle_button.clicked.connect(self.toggle_notifications)
        self.toggle_button.setStyleSheet("background-color: red; color: white;")
        buttons_grid.addWidget(self.toggle_button, 1, 1)

        # Añadir el layout de cuadrícula al layout principal
        left_layout.addLayout(buttons_grid)

        # Indicador de estado
        status_layout = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("Notifications: Disabled")
        status_layout.addWidget(self.status_label)
        self.status_indicator = QtWidgets.QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
        status_layout.addWidget(self.status_indicator)
        left_layout.addLayout(status_layout)

        # Ruta del archivo de configuración
        self.config_path_label = QtWidgets.QLabel(f"Config: {CONFIG_FILE}")
        left_layout.addWidget(self.config_path_label)

        # Área de registro
        self.log_area = QtWidgets.QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Log messages will appear here...")
        left_layout.addWidget(self.log_area)

        main_layout.addLayout(left_layout)

        # Lista de callbacks
        right_layout = QtWidgets.QVBoxLayout()
        callbacks_title = QtWidgets.QLabel("Current Callbacks")
        callbacks_title.setAlignment(QtCore.Qt.AlignCenter)
        right_layout.addWidget(callbacks_title)
        self.callbacks_list = QtWidgets.QListWidget()
        right_layout.addWidget(self.callbacks_list)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

    def create_shelf_tool(self):
        """
        Crea una herramienta en un estante para las notificaciones de Telegram.
        """
        # Obtener las shelves disponibles
        shelves = get_shelves()

        if not shelves:
            self.log_message("No shelves available")
            return

        # Mostrar diálogo para seleccionar la shelf
        selected_shelf = hou.ui.selectFromList(
            shelves,
            title="Select Shelf",
            message="Choose a shelf to add the tool to:",
            default_choices=(0,),
            clear_on_cancel=True
        )

        if selected_shelf:
            shelf_name = shelves[selected_shelf[0]]
            success = create_shelf_tool(
                shelf_name=shelf_name,
                tool_name="telegram_notifications",
                tool_label="Telegram Notifications",
                tool_script="""
import telegram_notifications
telegram_notifications.create_ui()
                """,
                tool_icon="MESSAGE"
            )

            if success:
                self.log_message(f"Tool successfully created in shelf: {shelf_name}")
            else:
                self.log_message("There was an error creating the tool")
        else:
            self.log_message("Tool creation cancelled.")

    def closeEvent(self, event):
        """
        Sobrescribe el evento de cierre para ocultar la ventana en lugar de cerrarla.
        """
        self.hide()  # Oculta la ventana
        event.ignore()  # Evita que la ventana se cierre completamente

    def log_message(self, message):
        """
        Añade un mensaje al área de registro.
        """
        self.log_area.append(message)

    def configure_telegram_bot(self):
        """
        Configura el bot de Telegram usando diálogos personalizados con botón de ayuda.
        """
        # Diálogo para BOT_TOKEN
        token_dialog = self.CustomInputDialog(
            "Configure Bot",
            "Enter your Telegram BOT_TOKEN:",
            self
        )
        
        if token_dialog.exec_() == QtWidgets.QDialog.Accepted:
            bot_token = token_dialog.get_input()
            if bot_token:
                # Diálogo para CHAT_ID
                chat_dialog = self.CustomInputDialog(
                    "Configure Bot",
                    "Enter your Telegram CHAT_ID:\n(Separate multiple IDs with commas)",
                    self
                )
                
                if chat_dialog.exec_() == QtWidgets.QDialog.Accepted:
                    chat_id = chat_dialog.get_input()
                    if chat_id:
                        config = {
                            "BOT_TOKEN": bot_token,
                            "CHAT_IDS": [cid.strip() for cid in chat_id.split(",")]
                        }
                        with open(CONFIG_FILE, "w") as f:
                            json.dump(config, f)
                        self.log_message(f"Config saved to: {CONFIG_FILE}")
                        self.config_path_label.setText(f"Config: {CONFIG_FILE}")
                        
                        # Mostrar mensaje de éxito
                        success_msg = QtWidgets.QMessageBox(self)
                        success_msg.setWindowTitle("Configuration Complete")
                        success_msg.setText("Configuration saved successfully!\n\nUse the 'Test Telegram Connection' button to verify your setup.")
                        success_msg.setIcon(QtWidgets.QMessageBox.Information)
                        success_msg.exec_()

    def test_telegram_connection(self):
        """
        Prueba la conexión con Telegram.
        """
        message = "🔄 Test message from Houdini - If you see this, the notification system is working!"
        if send_telegram_message(message):
            self.log_message("Test message sent successfully! Check your Telegram.")
        else:
            self.log_message("Failed to send test message. Check your BOT_TOKEN and CHAT_ID.")

    def toggle_notifications(self):
        """
        Habilita o deshabilita las notificaciones.
        """
        global NOTIFICATIONS_ENABLED
        NOTIFICATIONS_ENABLED = not NOTIFICATIONS_ENABLED
        if NOTIFICATIONS_ENABLED:
            self.toggle_button.setText("Disable Notifications")
            self.toggle_button.setStyleSheet("background-color: green; color: white;")
            self.status_label.setText("Notifications: Enabled")
            self.status_indicator.setStyleSheet("background-color: green; border-radius: 10px;")
            setup_render_callbacks()
        else:
            self.toggle_button.setText("Enable Notifications")
            self.toggle_button.setStyleSheet("background-color: red; color: white;")
            self.status_label.setText("Notifications: Disabled")
            self.status_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
            remove_all_callbacks()
        self.update_callbacks_list()

    def update_callbacks_list(self):
        """
        Actualiza la lista de callbacks en la UI.
        """
        callbacks = list(CALLBACK_REGISTRY)
        self.callbacks_list.clear()
        self.callbacks_list.addItems(callbacks)

    def show_help(self):
        """
        Muestra un diálogo de ayuda.
        """
        help_text = (
            "📝 <b>How to Get Telegram BOT_TOKEN and CHAT_ID</b><br><br>"
            "1. <b>Create a Telegram Bot:</b><br>"
            "   - Open Telegram and search for the <b>BotFather</b>.<br>"
            "   - Start a chat with BotFather and use the <b>/newbot</b> command.<br>"
            "   - Follow the instructions to create a new bot.<br>"
            "   - At the end, BotFather will give you a <b>BOT_TOKEN</b>.<br><br>"
            "2. <b>Get Your CHAT_ID:</b><br>"
            "   <b>Option 1: Using Raw Data Bot</b><br>"
            "   - Open Telegram and search for the <b>Raw Data Bot</b>.<br>"
            "   - Start a chat with the bot and send any message.<br>"
            "   - The bot will reply with your <b>CHAT_ID</b>.<br><br>"
            "   <b>Option 2: Using getUpdates API</b><br>"
            "   - Open Telegram and search for the bot you just created.<br>"
            "   - Start a chat with the bot and send any message.<br>"
            "   - Go to <b>https://api.telegram.org/bot&lt;YOUR_BOT_TOKEN&gt;/getUpdates</b>.<br>"
            "   - Look for the <b>chat.id</b> field in the response.<br><br>"
            "3. <b>Configure the Script:</b><br>"
            "   - Enter the <b>BOT_TOKEN</b> and <b>CHAT_ID</b> in the configuration dialog.<br>"
            "   - Separate multiple CHAT_IDs with commas if needed.<br><br>"
            "🔗 <b>For more details, visit:</b><br>"
            "<a href='https://core.telegram.org/bots#creating-a-new-bot'>Telegram Bot Documentation</a>"
        )
        help_dialog = QtWidgets.QMessageBox(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setTextFormat(QtCore.Qt.RichText)
        help_dialog.setText(help_text)
        help_dialog.exec_()

# Inicialización de la UI
ui = create_ui()
ui.log_message("\nSetting up render notifications...")
clear_duplicates()
remove_all_callbacks()
setup_render_callbacks()
ui.log_message("\nTelegram render notifications are now active!")
ui.log_message("\nNote: Run this script again if you create new render nodes!")
ui.update_callbacks_list()