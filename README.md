# Telegram Render Notifications for Houdini

This tool allows you to send Telegram notifications when renders in Houdini start, progress, complete, or fail. It is particularly useful for monitoring long renders remotely.

## Features

- **Easy Configuration**: Set up your Telegram bot and chat IDs directly from the user interface.
- **Customizable Notifications**: Receive notifications when renders start, finish, or encounter errors.
- **Connection Testing**: Verify your Telegram configuration before using it.
- **Shelf Integration**: Add the tool to any shelf in Houdini for quick access.
- **Render Progress Updates**: Get real-time updates on render progress, including estimated completion time.
- **Error Handling**: Detailed error messages are sent to Telegram if a render fails.
- **Render Statistics**: Track render times and performance statistics.

## Requirements

- Houdini 18.0 or higher.
- A Telegram account and a bot created via BotFather.

## Installation

1. **Download the Script**: Place the Python script in a directory accessible from Houdini.
2. **Run the Script**: In Houdini, open a Python editor and run the script to launch the user interface.
3. **Configure Your Bot**: Use the interface to enter your `BOT_TOKEN` and `CHAT_ID`.

📌 Where to Save the .py File
🔹 Option 1 (Recommended): Houdini Scripts Folder
Save the file in the following directory:
```
$HOUDINI_USER_PREF_DIR/scripts/
```
(On Windows, this is usually: C:/Users/YOUR_USER/Documents/houdiniXX.XX/scripts/.)

Then, in Houdini’s Source Editor, run:
```
import telegram_notifications
telegram_notifications.create_ui()
```
This should launch the script’s UI automatically.

🔹 If you get a ModuleNotFoundError when importing
Houdini might not be looking in the scripts/ folder. To fix this, manually add the path before importing:

```
import sys
sys.path.append("C:/Users/YOUR_USER/Documents/houdiniXX.XX/scripts")

import telegram_notifications
telegram_notifications.create_ui()
```

This tells Houdini where to find the script and should resolve the issue.

🔹 Option 2 (Easier, but Less Flexible): Houdini’s Python Library Folder
If you don’t want to modify sys.path, save the script in Houdini’s Python library folder:

C:\Program Files\Side Effects Software\Houdini XX.XX.X\python311\lib\
From there, it will work without any additional configuration:

```
import telegram_notifications
telegram_notifications.create_ui()
```
⚠ Downside: If you update Houdini, you’ll need to copy the script to the new version’s folder.



## Usage

- **Configuration**: Click "Configure Telegram Bot" to enter your bot details.
- **Test Connection**: Use the "Test Telegram Connection" button to ensure everything is set up correctly.
- **Enable/Disable Notifications**: Use the "Enable Notifications" button to turn notifications on or off.
- **Add to Shelf**: If you want quick access to the tool, use the "Create Shelf Tool" button to add it to a shelf in Houdini.
- **Render Progress**: During a render, you will receive progress updates, including estimated completion time and a progress bar.

## Support

For more information on how to obtain a `BOT_TOKEN` and `CHAT_ID`, consult the help section within the tool or visit the [official Telegram Bot documentation](https://core.telegram.org/bots#creating-a-new-bot).

## Contributing

Contributions are welcome. Please open an issue or a pull request if you have any improvements or encounter any problems.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
