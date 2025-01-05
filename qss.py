def apply_styles(widget):
    qss = """
    QWidget {
        background-color: #2b2b2b;
    }
    QTextEdit {
        color: #ffffff;
        background-color: #2b2b2b;
    }

    QMainWindow {
        background-color: #2b2b2b;
    }
    QTreeView {
        background-color: #2b2b2b;
        alternate-background-color: #3b3b3b;
        color: #ffffff;
        border: none;
    }
    QTreeView::item {
        height: 25px;
    }
    QTreeView::item:selected {
        background-color: #555555;
        color: #ffffff;
    }
    QTreeView::branch:has-siblings:!adjoins-item {
        border-image: url(none);
    }
    QTreeView::branch:has-siblings:adjoins-item {
        border-image: url(none);
    }
    QTreeView::branch:!has-children:!has-siblings:adjoins-item {
        border-image: url(none);
    }
    QTreeView::branch:has-children:!has-siblings:closed,
    QTreeView::branch:closed:has-children:has-siblings {
        image: url(icons/arrow-right-dark.png);
    }
    QTreeView::branch:open:has-children:!has-siblings,
    QTreeView::branch:open:has-children:has-siblings  {
        image: url(icons/arrow-down-dark.png);  /* 矢印の色を変更 */
    }
    """
    widget.setStyleSheet(qss)
