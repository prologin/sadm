import QtQuick 2.0
import SddmComponents 2.0

ComboBox {
    id: combo

    model: keyboard.layouts
    index: keyboard.currentLayout

    onValueChanged: keyboard.currentLayout = id

    Connections {
        target: keyboard

        onCurrentLayoutChanged: combo.index = keyboard.currentLayout
    }

    rowDelegate: Rectangle {
        color: "transparent"

        Image {
            id: img
            source: "/usr/share/sddm/flags/%1.png".arg(modelItem ? modelItem.modelData.shortName : "zz")

            anchors.margins: 4
            fillMode: Image.PreserveAspectFit

            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
        }

        Text {
            anchors.margins: 4
            anchors.left: img.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            verticalAlignment: Text.AlignVCenter

            text: modelItem ? modelItem.modelData.longName : "zz"
            font.pixelSize: 14
        }
    }
}
