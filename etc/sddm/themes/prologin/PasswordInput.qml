import QtQuick 2.0

FocusScope {
    property double capsLockWarnFade: 200
    property double capsLockWarnFadeIn: capsLockWarnFade
    property double capsLockWarnFadeOut: capsLockWarnFade

    property alias input: txtMain.input
    property alias image: txtMain.image

    height: 30

    Input {
        anchors.fill: parent
        id: txtMain
        input.echoMode: TextInput.Password
        input.anchors.rightMargin: parent.height
        focus: true
    }

    Text {
        id: capsLockWarn
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: width * 0.2
        height: parent.height * 0.8
        width: height
        text: '\u21ea'
        font.family: txtMain.input.font.family
        font.pointSize: txtMain.input.font.pointSize * 1.2
        font.bold: true
        color: txtMain.input.color
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        state: keyboard.capsLock ? 'activated' : ''
        opacity: 0
        states: [
            State {
                name: 'activated'
                PropertyChanges { target: capsLockWarn; opacity: 1; }
            },
            State {
                name: ''
                PropertyChanges { target: capsLockWarn; opacity: 0; }
            }
        ]
        transitions: [
            Transition {
                to: 'activated'
                NumberAnimation { target: capsLockWarn; property: 'opacity'; from: 0; to: 1; duration: capsLockWarnFadeIn; }
            },

            Transition {
                to: ''
                NumberAnimation { target: capsLockWarn; property: 'opacity'; from: 1; to: 0; duration: capsLockWarnFadeOut; }
            }
        ]

    }
}
