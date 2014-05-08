(load "~/.tuareg-mode/tuareg.el")

(setq auto-mode-alist
      (append '(("\\.ml[ily]?$" . tuareg-mode))
              auto-mode-alist))
