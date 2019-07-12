import QtQuick 2.12
import QtQuick.Controls 2.5

TextField {
    property alias imageSource: image.icon.source
    property alias imageColor: image.icon.color
    property alias imageWidth: image.width
    property int imageSpacing: padding

    property bool keyboardWarnings: false

    function wiggle() {
        animWiggle.start()
    }

    id: input

    SequentialAnimation {
        id: animWiggle
        running: false
        alwaysRunToEnd: true
        XAnimator { target: input; to: 10; duration: 120; easing.type: Easing.OutBounce; }
        XAnimator { target: input; to: -10; duration: 120; easing.type: Easing.OutBounce; }
        XAnimator { target: input; to: 0; duration: 120; easing.type: Easing.OutBounce; }
    }

    Button {
        focusPolicy: Qt.NoFocus
        id: image
        width: imageWidth
        height: imageWidth
        anchors.verticalCenter: input.verticalCenter
        anchors.right: input.left
        anchors.rightMargin: imageSpacing
        padding: 0
        background: null
        opacity: input.focus ? 1 : .8;
    }

    font: mainFont
    color: Qt.hsla(0, 0, .9, 1)
    placeholderTextColor: Qt.hsla(0, 0, .5, 1)

    leftPadding: padding
    rightPadding: padding + (keyboardWarnings ? kbWarnings.width + padding : 0)
    topPadding: padding
    bottomPadding: topPadding

    background: Rectangle {
        color: "#20000000"
        gradient: Gradient {
            GradientStop { color: "#20000000"; position: 1 }
            GradientStop { color: "#10000000"; position: 0 }
        }
        border.color: input.focus ? activeWhite : inactiveWhite
        radius: 4

        Text {
            id: kbWarnings
            font: { const f = Qt.font(input.font); f.pointSize *= .8; return f; }
            lineHeight: 1
            color: input.color
            visible: keyboardWarnings
            text: {
                const parts = [];
                if (keyboard.capsLock) parts.push("↑")
                if (keyboard.numLock) parts.push("123")
                return parts.join("  ")
            }
            ToolTip.visible: keyboardWarnings && hovered;
            ToolTip.delay: tooltipDelay
            ToolTip.text: {
                const parts = [];
                if (keyboard.capsLock) parts.push("CapsLock")
                if (keyboard.numLock) parts.push("NumLock")
                return parts.join(", ")
            }
            anchors.right: parent.right;
            anchors.rightMargin: input.padding
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
