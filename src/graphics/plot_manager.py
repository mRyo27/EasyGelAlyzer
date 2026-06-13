import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'MS Gothic'

__all__ = ["Figure", "FigureCanvasTkAgg", "plt"]
