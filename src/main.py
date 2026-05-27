import tkinter as tk

from app import EasyGelAlyzerApp


def main():
    root = tk.Tk()
    app = EasyGelAlyzerApp(root)
    root.update_idletasks()
    app.fit_image_to_canvas()
    root.mainloop()


if __name__ == "__main__":
    main()
