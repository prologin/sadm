import QtQuick 2.12
import QtQuick.Layouts 1.12
import QtQuick.Controls 2.5
import SddmComponents 2.0

Item {
    signal attemptLogin(string login, string password, int session)

    property font mainFont: Qt.font({"family": "Cantarell", "pointSize": 13})
    property font largeFont: Qt.font({"family": "Cantarell", "pointSize": 17})
    property font timeFont: Qt.font({"family": "Cantarell", "pointSize": 42})
    property color textColor: "white"
    property color activeWhite: "#aaffffff"
    property color inactiveWhite: "#33ffffff"
    property int tooltipDelay: 500

    property alias motd: textMotd.text

    id: ui
    state: "idle"

    function onLoginSucceeded() {
        ui.state = "idle"
        inputPassword.text = ""
        errorMessage.state = "hidden"
    }

    function onLoginFailed() {
        ui.state = "idle"
        inputPassword.text = ""
        textErrorMessage.state = "visible"
    }

    function onLoginAttempt() {
        ui.state = "connecting"
        textErrorMessage.state = "hidden"
        inputLogin.focus = false
        inputPassword.focus = false
    }

    Timer {
        id: delayedLogin
        interval: 800
        running: false
        repeat: false
        onTriggered: {
	    attemptLogin(inputLogin.text, inputPassword.text, comboSession.currentIndex)
        }
    }

    function doLogin() {
        if (!inputLogin.text.length) {
            inputLogin.focus = true
            inputLogin.wiggle();
            return
        }
        if (!inputPassword.text.length) {
            inputPassword.focus = true
            inputPassword.wiggle();
            return
        }
        onLoginAttempt()
        delayedLogin.restart()
    }

    function motd() {
        return textMotd;
    }

    function time() {
        return texTime;
    }

    function errorMessage() {
        return textErrorMessage;
    }

    function loginInput() {
        return inputLogin;
    }

    function passwordInput() {
        return inputPassword;
    }

    function loginButton() {
        return buttonLogin;
    }

    function powerOffButton() {
        return buttonPoweroff;
    }

    function rebootButton() {
        return buttonReboot;
    }

    function bg1() {
        return rectBg1;
    }

    function bg2() {
        return rectBg2;
    }

    Component.onCompleted: inputLogin.focus = true

    // Fallback return key.
    Keys.onReturnPressed: doLogin()

    // Background layer 1
    Rectangle {
        id: rectBg1;
        anchors.fill: parent
        color: "#670d10"
        gradient: Gradient {
            GradientStop {
                color: "#670d10"
                position: 0
            }
            GradientStop {
                color: "#092756"
                position: 1
            }
        }
    }

    // Background layer 2
    Rectangle {
        id: rectBg2;
        anchors.fill: parent
        color: "#39addb"
        opacity: .3
        gradient: Gradient {
            GradientStop {
                color: "#39addb"
                position: 0
            }
            GradientStop {
                color: "#2a3c57"
                position: 1
            }
        }
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        spacing: 11

    ColumnLayout {
        id: mainColumn
        Layout.preferredWidth: 300
        Layout.maximumWidth: 300
        spacing: 11
        clip: false
        anchors.horizontalCenter: parent.horizontalCenter

        // Theme logo.
        Image {
            Layout.fillWidth: true
            source: "/opt/prologin/sddm-logo.svg"
            fillMode: Image.PreserveAspectFit
            // This is the only way to work around QML being an utter piece of crap.
            sourceSize: Qt.size(width, 0)
        }

        // Message of the day.
        Text {
            id: textMotd
            Layout.fillWidth: true
            font: largeFont
            color: textColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        // Clock.
        Column {
            id: container
            Layout.fillWidth: true

            property date dateTime: new Date()

            Timer {
                interval: 1000; running: true; repeat: true;
                onTriggered: container.dateTime = new Date()
            }

            Text {
                id: time
                anchors.horizontalCenter: parent.horizontalCenter
                text : Qt.formatTime(container.dateTime, "hh:mm")
                color: textColor
                font: timeFont
            }
        }
    }

    ColumnLayout {
        id: formColumn
        Layout.preferredWidth: 300
        Layout.maximumWidth: 300
        anchors.top: mainColumn.bottom
        anchors.topMargin: spacing
        spacing: 11
        clip: false
        anchors.horizontalCenter: parent.horizontalCenter

        // Hostname.
        Text {
            id: textHostname
            text: sddm.hostName
            anchors.horizontalCenter: parent.horizontalCenter
            color: textColor
            font: largeFont
        }

        // Spacer.
        Item { Layout.preferredHeight: mainColumn.spacing * 3 }

        // Error message.
        Text {
            id: textErrorMessage
            Layout.fillWidth: true
            text: textConstants.loginFailed
            font: mainFont
            color: textColor
            opacity: 0
            state: "hidden"
            states: [
                State {
                    name: "visible"
                    PropertyChanges { target: textErrorMessage; opacity: 1; }
                }
            ]
            transitions: [
                Transition {
                    to: "*"
                    reversible: true
                    NumberAnimation { properties: "opacity"; duration: 250; easing.type: Easing.InOutQuad; }
                }
            ]
        }

        // Username input.
        MyImageInput {
            id: inputLogin
            Layout.fillWidth: true
            placeholderText: textConstants.userName
            imageSource: "img/user.svg"
            imageWidth: 26
            imageColor: textColor
            padding: 11
        }

        // Password input.
        MyImageInput {
            id: inputPassword
            Layout.fillWidth: true
            placeholderText: textConstants.password
            echoMode: TextField.Password
            imageSource: "img/key.svg"
            imageWidth: 26
            imageColor: textColor
            padding: 11
            keyboardWarnings: true
        }

        // Login button.
        MyButton {
            id: buttonLogin
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            transform: Translate { id: buttonLoginTranslate }
            padding: 11
            text: textConstants.login
            onClicked: doLogin()
            Keys.onReturnPressed: doLogin()
            Keys.onSpacePressed: doLogin()
        }
    }

        ColumnLayout {
            id: optionsLayout
            Layout.preferredWidth: 300
            Layout.maximumWidth: 300
            anchors.top: formColumn.bottom
            anchors.topMargin: spacing * 3
            spacing: 11
            clip: false
            anchors.horizontalCenter: parent.horizontalCenter

        // Session (window manager) combo.
        MyComboBox {
            id: comboSession
            Layout.alignment: Qt.AlignCenter
            anchors.horizontalCenter: parent.horizontalCenter

            model: sessionModel
            currentIndex: sessionModel.lastIndex

            function labelText(model, modelData) {
                return model.name;
            }
        }

        // Keyboard layout combo.
        MyComboBox {
            id: comboLocale
            Layout.alignment: Qt.AlignCenter
            anchors.horizontalCenter: parent.horizontalCenter

            model: keyboard.layouts
            currentIndex: keyboard.currentLayout

            onCurrentIndexChanged: keyboard.currentLayout = currentIndex

            Connections {
                target: keyboard
                onCurrentLayoutChanged: comboLocale.currentIndex = keyboard.currentLayout
            }

            function labelText(model, modelData) {
                return modelData.longName;
            }

            function imageSource(model, modelData) {
                return "/usr/share/sddm/flags/%1.png".arg(modelData.shortName);
            }
        }
    }

    }

    RowLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: mainColumn.spacing * 3
        spacing: mainColumn.spacing * 3

        MyConfirmButton {
            id: buttonPoweroff
            icon.source: "img/poweroff.svg"
            onConfirmed: sddm.powerOff()
        }

        MyConfirmButton {
            id: buttonReboot
            icon.source: "img/reboot.svg"
            onConfirmed: sddm.reboot()
        }
    }

    SequentialAnimation {
        id: animBounce
        running: false
        loops: Animation.Infinite
        NumberAnimation { target: buttonLoginTranslate; property: "x"; to: inputPassword.width / 2 - buttonLogin.width / 2; duration: 600; easing.type: Easing.OutBounce; }
        PauseAnimation { duration: 400 }
        NumberAnimation { target: buttonLoginTranslate; property: "x"; to: -(inputPassword.width / 2 - buttonLogin.width / 2); duration: 600; easing.type: Easing.OutBounce; }
        PauseAnimation { duration: 400 }
    }

    ParallelAnimation {
        id: animMorph
        alwaysRunToEnd: true
        NumberAnimation { target: buttonLogin; property: "Layout.leftMargin"; to: inputPassword.width / 2 - inputPassword.height / 2; easing.type: Easing.InOutQuad; duration: 250; }
        NumberAnimation { target: buttonLogin; property: "Layout.rightMargin"; to: inputPassword.width / 2 - inputPassword.height / 2; easing.type: Easing.InOutQuad; duration: 250; }
        NumberAnimation { target: buttonLogin; property: "radius"; to: buttonLogin.height / 2; easing.type: Easing.InOutQuad; duration: 250; }
        NumberAnimation { target: buttonLogin; property: "contentOpacity"; to: 0; easing.type: Easing.InOutQuad; duration: 250; }
        onFinished: { animBounce.start() }
    }

    ParallelAnimation {
        id: animUnMorph
        alwaysRunToEnd: true
        onStarted: { animBounce.stop(); }
        NumberAnimation { target: buttonLoginTranslate; property: "x"; to: 0; duration: 250; easing.type: Easing.InOutQuad; }
        NumberAnimation { target: buttonLogin; property: "Layout.leftMargin"; to: 0; easing.type: Easing.InOutQuad; duration: 250; }
        NumberAnimation { target: buttonLogin; property: "Layout.rightMargin"; to: 0; easing.type: Easing.InOutQuad; duration: 250; }
        NumberAnimation { target: buttonLogin; property: "radius"; to: 4; easing.type: Easing.InOutQuad; duration: 250; }
        NumberAnimation { target: buttonLogin; property: "contentOpacity"; to: 1; easing.type: Easing.InOutQuad; duration: 250; }
    }

    states: [
        State {
            name: "idle"
            StateChangeScript { script: animUnMorph.start(); }
        },
        State {
            name: "connecting"
            PropertyChanges { target: inputLogin; opacity: .6 }
            PropertyChanges { target: inputPassword; opacity: .6 }
            PropertyChanges { target: mainColumn; enabled: false }
            PropertyChanges { target: optionsLayout; enabled: false }
            StateChangeScript { script: animMorph.start(); }
        }
    ]

    transitions: [
        Transition {
            to: "*"
            reversible: true
            NumberAnimation { properties: "opacity,width"; duration: 250; easing.type: Easing.InOutQuad; }
        }
    ]
}
