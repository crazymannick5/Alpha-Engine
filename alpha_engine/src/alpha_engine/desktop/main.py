def main():
    try:
        from PySide6.QtWidgets import QApplication,QMainWindow,QTabWidget,QLabel,QWidget,QVBoxLayout
    except ImportError as exc:
        raise SystemExit('Desktop extra not installed: pip install .[desktop]') from exc
    import sys
    app=QApplication(sys.argv); win=QMainWindow(); win.setWindowTitle('Personal Alpha Engine'); tabs=QTabWidget()
    for name in ['Overview','Opportunity Radar','Review Queue','Evidence & Data','Paper Portfolio','Outcomes & Evaluation','Operations','Providers & Data Queries','Budgets','Permissions','Notifications','Registries','Health & Recovery','Settings']:
        page=QWidget(); layout=QVBoxLayout(page); layout.addWidget(QLabel(f'{name} — central hub view')); tabs.addTab(page,name)
    win.setCentralWidget(tabs); win.resize(1200,800); win.show(); sys.exit(app.exec())
if __name__=='__main__': main()
