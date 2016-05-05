/***************************************************************************
* Copyright (c) 2013 Abdurrahman AVCI <abdurrahmanavci@gmail.com>
*
* Permission is hereby granted, free of charge, to any person
* obtaining a copy of this software and associated documentation
* files (the "Software"), to deal in the Software without restriction,
* including without limitation the rights to use, copy, modify, merge,
* publish, distribute, sublicense, and/or sell copies of the Software,
* and to permit persons to whom the Software is furnished to do so,
* subject to the following conditions:
*
* The above copyright notice and this permission notice shall be included
* in all copies or substantial portions of the Software.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
* OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
* THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
* OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
* ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
* OR OTHER DEALINGS IN THE SOFTWARE.
*
***************************************************************************/

import QtQuick 2.0
import SddmComponents 2.0

Rectangle {
    id: container

    property color textColor: '#fafafa'
    property color brandColor: '#33449d'

    function inputKeyEvent(event) {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            login();
            event.accepted = true
        }
    }

    function login() {
        sddm.login(name.text, password.text, session.index);
    }

    LayoutMirroring.enabled: Qt.locale().textDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    TextConstants { id: textConstants }

    Connections {
        target: sddm

        onLoginSucceeded: {
            errorMessage.color = "steelblue"
            errorMessage.text = textConstants.loginSucceeded
        }

        onLoginFailed: {
            errorMessage.color = "red"
            errorMessage.text = textConstants.loginFailed
        }
    }

    Background {
        anchors.fill: parent
        source: config.backgroundPattern
        fillMode: Image.Tile
        onStatusChanged: {
            if (status == Image.Error && source !== config.defaultBackground) {
                source = config.defaultBackground
            }
        }
    }

    Image {
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: -width / 2
        width: parent.width / 3
        height: parent.height / 3
        sourceSize.width: width
        sourceSize.height: height
        source: config.background
        fillMode: Image.PreserveAspectFit
        clip: true
        focus: false
        smooth: true
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        anchors.topMargin: 90
        anchors.rightMargin: 120

        Clock {
            id: clock
            anchors.top: parent.top
            anchors.right: parent.right

            color: textColor
            timeFont.family: "Oxygen,Oxygen-Sans,sans-serif"
        }

        Rectangle {
            id: rectangle
            anchors.right: clock.right
            anchors.left: clock.left
            anchors.top: clock.bottom
            anchors.topMargin: 200

            Column {
                id: mainColumn
                anchors.centerIn: parent
                spacing: 12

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: textColor
                    verticalAlignment: Text.AlignVCenter
                    height: text.implicitHeight
                    width: parent.width
                    text: sddm.hostName
                    wrapMode: Text.WordWrap
                    font.pixelSize: 24
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }

                Input {
                    id: name
                    input.color: textColor
                    image.source: 'user.png'
                    anchors.left: parent.left
                    anchors.right: parent.right

                    input.focus: true

                    input.text: userModel.lastUser

                    KeyNavigation.backtab: rebootButton
                    KeyNavigation.tab: password
                    Keys.onPressed: inputKeyEvent(event)
                }

                PasswordInput {
                    id: password
                    input.color: textColor
                    image.source: 'lock.png'
                    anchors.left: parent.left
                    anchors.right: parent.right

                    KeyNavigation.backtab: name
                    KeyNavigation.tab: session
                    Keys.onPressed: inputKeyEvent(event)
                }

                // separator
                Item {
                    height: 30
                    width: parent.width
                }

                Row {
                    spacing: 4
                    width: parent.width / 2
                    z: 100

                    Column {
                        z: 100
                        width: parent.width * 1.3
                        spacing : 4
                        anchors.bottom: parent.bottom

                        Text {
                            id: lblSession
                            width: parent.width
                            color: textColor
                            text: textConstants.session
                            wrapMode: TextEdit.WordWrap
                            font.bold: true
                            font.pixelSize: 12
                        }

                        ComboBox {
                            id: session
                            width: parent.width
                            height: 30
                            font.pixelSize: 14

                            textColor: textColor
                            focusColor: brandColor
                            hoverColor: brandColor
                            arrowIcon: "angle-down.png"

                            model: sessionModel
                            index: sessionModel.lastIndex

                            KeyNavigation.backtab: password
                            KeyNavigation.tab: layoutBox
                        }
                    }

                    Column {
                        z: 101
                        width: parent.width * 0.7
                        spacing : 4
                        anchors.bottom: parent.bottom

                        Text {
                            id: lblLayout
                            width: parent.width
                            color: textColor
                            text: textConstants.layout
                            wrapMode: TextEdit.WordWrap
                            font.bold: true
                            font.pixelSize: 12
                        }

                        LayoutBox {
                            id: layoutBox
                            width: parent.width
                            height: 30
                            font.pixelSize: 14

                            arrowIcon: "angle-down.png"

                            KeyNavigation.backtab: session
                            KeyNavigation.tab: loginButton
                        }
                    }
                }

                Column {
                    width: parent.width
                    Text {
                        id: errorMessage
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: textConstants.prompt
                        color: textColor
                        font.pixelSize: 10
                    }
                }

                Row {
                    spacing: 4
                    anchors.horizontalCenter: parent.horizontalCenter
                    property int btnWidth: Math.max(loginButton.implicitWidth,
                                                    shutdownButton.implicitWidth,
                                                    rebootButton.implicitWidth, 80) + 8
                    Button {
                        id: loginButton
                        text: textConstants.login
                        width: parent.btnWidth
                        color: brandColor

                        onClicked: login()

                        KeyNavigation.backtab: layoutBox
                        KeyNavigation.tab: shutdownButton
                    }

                    Button {
                        id: shutdownButton
                        text: textConstants.shutdown
                        width: parent.btnWidth
                        color: brandColor

                        onClicked: sddm.powerOff()

                        KeyNavigation.backtab: loginButton
                        KeyNavigation.tab: rebootButton
                    }

                    Button {
                        id: rebootButton
                        text: textConstants.reboot
                        width: parent.btnWidth
                        color: brandColor

                        onClicked: sddm.reboot()

                        KeyNavigation.backtab: shutdownButton
                        KeyNavigation.tab: name
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        if (name.text === "")
            name.focus = true
        else
            password.focus = true
    }
}
