import QtQuick 2.12
import QtQuick.Controls 2.5

Button {
    id: btn

    property alias color: content.color
    property alias contentOpacity: content.opacity
    property alias radius: bg.radius

    contentItem: Text {
        id: content
        text: btn.text
        font: mainFont
        color: "white"
    }

    Gradient {
        id: bgActive
        GradientStop { color: "#d0451b"; position: 1 }
        GradientStop { color: "#bc3315"; position: .05 }
    }

    Gradient {
        id: bgNormal
        GradientStop { color: "#d0451b"; position: .05 }
        GradientStop { color: "#bc3315"; position: 1 }
    }

    background: Rectangle {
        id: bg
        radius: 4
        border.color: "#942911";
        gradient: btn.enabled && (btn.hovered || btn.focus || btn.activeFocus) ? bgActive : bgNormal
    }

    MouseArea {
        enabled: false  // this is only for the cursor shape
        anchors.fill: parent
        cursorShape: "PointingHandCursor"
    }
}
