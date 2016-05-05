import QtQuick 2.0

FocusScope {
    height: 30

    property alias image: image
    property alias input: txtMain
    property color textColor: '#fafafa'
    property color lineColor: '#77fafafa'
    property int lineWidth: 1

    MouseArea {
        id: mouseArea
        anchors.fill: parent

        cursorShape: Qt.IBeamCursor

        hoverEnabled: true

        onEntered: if (line.state === "") line.state = "hover";
        onExited: if (line.state === "hover") line.state = "";
        onClicked: parent.focus = true;
    }

    Row {
        anchors.fill: parent
        spacing: 10

        Image {
            id: image
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: parent.height
            fillMode: Image.PreserveAspectFit
        }

        Column {
            width: parent.width - image.width - parent.spacing
            height: parent.height
            spacing: 0

            TextInput {
                id: txtMain
                height: parent.height - 1
                anchors.left: parent.left
                anchors.right: parent.right
                color: textColor
                clip: true
                focus: true
                verticalAlignment: TextInput.AlignVCenter
                passwordCharacter: '\u25cf'
                font.pixelSize: 14

            }

            Rectangle {
                id: line
                width: parent.width
                height: lineWidth
                color: lineColor
            }
        }
    }
}
