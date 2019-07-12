/*

A minimal but powerful theme suited for the Prologin finals.

This theme features:

  * A fairly standard username/password form.
    * The password input features CapsLock & NumLock indicators.
    * Attempting to login while having an empty field focuses the empty field and shakes it.
  * A “flat” locale selection (no annoying dropdown).
  * A “flat” keyboard layout selection (no annoying dropdown).
  * A remote control through WebSocket; to enable, in theme.conf set websocket= to a valid
    ws://… address. The theme will try to connect every few seconds and retry on connection lost.
    Once connected, every received text message will be parsed as JSON. The protocol understands
    two commands:
      * {"eval": "1 + 2"} → eval("1 + 2") (Javascript), replies with the result
      * {"motd": "hello"} → sets ui.motd to "hello", doesn't reply anything
  * An animated/morphing login button.
  * Shutdown and reboot buttons with a confirmation step: two clicks/keypreses are necessary:
    [REBOOT] → [Sure? ] → *reboots*

Known issues:

  * If the password is incorrect, the animation works fine because sddm stays alive while calling
    PAM 'auth' stage, during which the login/password is checked.
    But if the password is correct, the 'auth' stage succeeds and sddm-greeter (UI frontend) exits,
    effectively freezing the screen until the desktop environment takes over. Unfortunately for
    Prologin, the long-running pam_exec script is called in the 'session' PAM stage, just after
    'auth' has succeeded. This means the animation will look like it's stuck while in fact sddm UI
    just exited normally. If an error is returned during 'session' initialization – which is an
    okay behavior as far as PAM is concerned – sddm won't be able to recover. An sddm restart is
    necessary. Computers suck.
  * The “flat” selectors are difficult to navigate using the keyboard because of lack of a proper
    'focused' state. That should be an easy fix though, look into MyComboBox.qml.

Files:

  * Main.qml (this file): theme root, contains logic, no UI
  * UserInterface.qml: UI root, instanciated in Main.qml
  * MyButton.qml: a highly customized button
  * MyComboBox.qml: an horizontal list of options; options have a label and optionally an image
  * MyConfirmButton.qml: an image button with a confirm flow before running the "on click" function
  * MyImageInput.qml: a text input with an image on the left (for the username & password)

*/

import QtQuick 2.12
import SddmComponents 2.0
import QtWebSockets 1.1

Item {
    id: root

    property int selectedSessionIndex: sessionModel.lastIndex

    TextConstants { id: textConstants }

    Connections {
        target: sddm
        onLoginSucceeded: ui.onLoginSucceeded()
        onLoginFailed: ui.onLoginFailed()
    }

    WebSocket {
        id: sock
        url: config.websocket
        active: !!config.websocket
        onTextMessageReceived: {
            var data = JSON.parse(message)
            if (data.eval) {
                const result = eval(data.eval);
                sock.sendTextMessage(result);
            } else if (data.motd) {
                ui.motd = data.motd;
            }
        }
    }

    Timer {
        id: sockReconnectTimer
        interval: 2500
        running: sock.active
        repeat: true
        onTriggered: {
            if (sock.status !== WebSocket.Open) {
                // Reconnect.
                sock.active = false
                sock.active = true
            }
        }
    }

    UserInterface {
        id: ui
        anchors.fill: parent
        focus: true

        Component.onCompleted: {
            ui.attemptLogin.connect(function(login, password, session) {
                sddm.login(login, password, session)
            })
        }
    }
}
