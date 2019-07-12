import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.12

ListView {
    id: view
    orientation: Qt.Horizontal
    spacing: 11
    implicitWidth: contentItem.childrenRect.width
    implicitHeight: contentItem.childrenRect.height
    activeFocusOnTab: true
    boundsBehavior: Flickable.StopAtBounds  // no scroll/swipe movement

    // To be overriden.
    function labelText() { return "" }
    // To be overriden.
    function imageSource() { return "" }

    delegate: RadioDelegate {
        id: delegate
        opacity: enabled ? (delegate.checked ? 1 : .7) : .4
        onClicked: if (checked) view.currentIndex = index

        contentItem: RowLayout {
            spacing: view.spacing

            Image {
                visible: imageSource(model, modelData) !== null
                source: imageSource(model, modelData)
                sourceSize: Qt.size(0, text.height)
                fillMode: Image.PreserveAspectFit
            }

            Text {
                id: text
                text: labelText(model, modelData)
                color: textColor
                verticalAlignment: Text.AlignVCenter
            }
        }

        indicator: null

        background: Rectangle {
            radius: 4
            color: "#20000000"
            gradient: Gradient {
                GradientStop { color: "#20000000"; position: 1 }
                GradientStop { color: "#10000000"; position: 0 }
            }
            border.width: 1
            border.color: delegate.checked ? activeWhite : inactiveWhite
        }

        checked: index == view.currentIndex
        ButtonGroup.group: buttonGroup
    }

    ButtonGroup {
        id: buttonGroup
    }
}
