import QtQuick 2.12
import QtQuick.Controls 2.5

Pane {
    id: wrap

    property alias icon: btn.icon

    signal confirmed()

    state: "normal"
    padding: 0
    contentWidth: state == "normal" ? btn.implicitWidth : confirm.implicitWidth
    contentHeight: state == "normal" ? btn.implicitHeight : confirm.implicitHeight

    background: null

    Keys.onEscapePressed: wrap.state = "normal"

    Button {
        id: btn
        anchors.fill: parent
        padding: 11
        Component.onCompleted: updateColor()
        background: Rectangle {
            color: "transparent"
            border.width: 1
            radius: 4
            border.color: parent.activeFocus || parent.hovered ? activeWhite : inactiveWhite
        }
        onClicked: {
            wrap.state = "confirm"
            confirm.focus = true
        }
        onActiveFocusChanged: updateColor()
        onHoveredChanged: updateColor()
        function updateColor() {
            icon.color = hovered || activeFocus ? activeWhite : inactiveWhite
        }
    }

    Button {
        id: confirm
        anchors.fill: parent
        visible: false
        text: "You sure?"
        icon: btn.icon
        padding: 11
        Component.onCompleted: { updateColor(); contentItem.color = activeWhite }
        background: Rectangle {
            color: "transparent"
            border.width: 1
            radius: 4
            border.color: parent.activeFocus || parent.hovered ? activeWhite : inactiveWhite
        }
        onClicked: {
            wrap.state = "normal"
            wrap.confirmed()
            btn.focus = true
        }
        onActiveFocusChanged: { updateColor(); if (!activeFocus) wrap.state = "normal" }
        onHoveredChanged: updateColor()
        function updateColor() {
            icon.color = hovered || activeFocus ? activeWhite : inactiveWhite
        }
    }

    states: [
        State {
            name: "confirm"
            PropertyChanges { target: btn; visible: false }
            PropertyChanges { target: confirm; visible: true }
        }
    ]
}
