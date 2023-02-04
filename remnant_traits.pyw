__author__ = "E_A83"

from PyQt6 import QtGui, QtCore, QtWidgets, uic
import os
import sys
import re
import zlib

# change icon of taskbar
if os.name == 'nt':
    import ctypes
    myappid = 'RemnantTraits_0.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

workpath = ""
if hasattr(sys, '_MEIPASS'):
    workpath = sys._MEIPASS + "\\"

TRAIT_LENGTH = 53


class TableModel(QtCore.QAbstractTableModel):
    update_error = QtCore.pyqtSignal(int)

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        self.colors = dict()

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.ItemDataRole.DisplayRole or role == QtCore.Qt.ItemDataRole.EditRole:
                return self._data[index.row()][index.column()]
            if role == QtCore.Qt.ItemDataRole.BackgroundRole:
                color = self.colors.get((index.row(), index.column()))
                if color is not None:
                    return color

    def setData(self, index, value, role):
        if role == QtCore.Qt.ItemDataRole.EditRole:
            if type(value) == int and 1 <= value <= 255:
                self._data[index.row()][index.column()] = value
                return True
            else:
                self.update_error.emit(value)
        return False

    def flags(self, index):
        return QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsEditable

    def change_color(self, row, column, color):
        ix = self.index(row, column)
        self.colors[(row, column)] = color
        self.dataChanged.emit(ix, ix, (QtCore.Qt.ItemDataRole.BackgroundRole,))


class Remnant(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.save_enabled = False
        self.traits_location = None
        self.profile_data = None
        self.profiles_traits = None
        self.fn = None

    def initUI(self):
        uic.loadUi(workpath + "remnant.ui", self)
        self.save_button.clicked.connect(self.save)
        self.action_about.setIcon(QtGui.QIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion)))
        self.action_about.triggered.connect(self.about)
        self.action_about_qt.setIcon(QtGui.QIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton)))
        self.action_about_qt.triggered.connect(self.about_qt)
        self.action_quit.setIcon(QtGui.QIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton)))
        self.action_quit.triggered.connect(self.close)
        self.action_save.setIcon(QtGui.QIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)))
        self.action_save.triggered.connect(self.save)
        self.action_open.setIcon(QtGui.QIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)))
        self.action_open.triggered.connect(self.open)        
        
        self.setWindowIcon(QtGui.QIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)))
        self.setWindowTitle('Remnant Traits :: {0}'.format(os.getlogin()))
        self.setFixedWidth(self.size().width())
        self.center()
        self.show()

    def open(self):
        default_path = os.path.join("c:\\Users", os.getlogin(), "AppData\Local\Remnant\Saved\SaveGames")
        fn = QtWidgets.QFileDialog.getOpenFileName(self,  "open profile", default_path, "*.sav")
        if fn[0]:
            self.fn = fn[0]
            self.profile_path.setText(fn[0])
            f = open(fn[0], "rb")
            self.profile_data = f.read()
            f.close()
            traits = []
            trait_names = re.findall(b"/Game/World_Base/Items/Traits/Trait_.?.?.?.?.?.?.?.?.?.?.?.?.?.?.?.?.?.?.?.?\.", self.profile_data)
            if not trait_names:
                QtWidgets.QMessageBox.information(self, "Open", "Traits not found!", QtWidgets.QMessageBox.StandardButton.Ok)
                return
            for trait in trait_names:
                traits.append(["Class", trait.split(b".")[0].split(b"/")[-1].decode(), 0])
            profile_names = re.findall(b"/Game/_Core/Archetypes/Archetype_.?.?.?.?.?.?.?.?_UI\.", self.profile_data)
            self.profiles_traits = []
            counter = 1
            for trait in trait_names[1:]:
                if b"Vigor" in trait:
                    self.profiles_traits.append([counter, 0])
                    counter = 0
                counter += 1
            self.profiles_traits.append([counter, 0])
            index = 0
            t = 0
            for profile in range(len(self.profiles_traits)):
                profile_class = profile_names[profile].split(b"_")[-2].decode()
                index = self.profile_data.find(b'Traits', self.profile_data.find(b'PersistenceKeys', index)) + 6 + 73
                self.profiles_traits[profile][1] = index
                pos = 0
                for i in range(self.profiles_traits[profile][0]):
                    points = int.from_bytes(self.profile_data[index + pos + 28:index + pos + 30], "big")
                    traits[t][0] = profile_class
                    traits[t][2] = points
                    pos += TRAIT_LENGTH
                    t += 1
            model = TableModel(traits)
            model.update_error.connect(self.update_error)
            self.tableView.setModel(model)
            self.tableView.setColumnWidth(0, 80)
            self.tableView.setColumnWidth(1, 150)
            self.tableView.setColumnWidth(2, 50)
            self.save_enabled = True

            t = 0
            for p in range(len(self.profiles_traits)):
                for i in range(self.profiles_traits[p][0]):
                    if p % 2 != 0:
                        self.tableView.model().change_color(t, 0, QtGui.QColor(220, 220, 220))
                        self.tableView.model().change_color(t, 1, QtGui.QColor(220, 220, 220))
                        self.tableView.model().change_color(t, 2, QtGui.QColor(220, 220, 220))
                    t += 1

    @QtCore.pyqtSlot(int)
    def update_error(self, value):
        QtWidgets.QMessageBox.information(self, "Change Trait Points", "Value should be between 1 and 255, got {}".format(value), QtWidgets.QMessageBox.StandardButton.Ok)

    def save(self):
        if not self.save_enabled or not self.fn: return
        rows = self.tableView.model().rowCount(0)
        table = self.tableView.model()
        data = bytearray(self.profile_data)

        t = 0
        for p in range(len(self.profiles_traits)):
            index = self.profiles_traits[p][1]
            for i in range(self.profiles_traits[p][0]):
                data[index+i*TRAIT_LENGTH+28:index+i*TRAIT_LENGTH+30] = table.index(t, 2).data().to_bytes(2, "big")
                t += 1

        data[:4] = zlib.crc32(data[4:]).to_bytes(4, "little")
        f = open(self.fn, "wb")
        f.write(data)
        f.close()
        QtWidgets.QMessageBox.information(self,  "Save", "Saved new trait points data!", QtWidgets.QMessageBox.StandardButton.Ok)

    def about(self):
        QtWidgets.QMessageBox.about(self, "About", "Author: E_A83")

    def about_qt(self):
        QtWidgets.QMessageBox.aboutQt(self, "About Qt")

    def center(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(self, "Quit", "Are you sure to quit?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            event.accept()
        else:event.ignore()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    _main = Remnant()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
