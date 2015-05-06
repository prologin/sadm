(load "~/.tuareg-mode/tuareg.el")

(setq auto-mode-alist
      (append '(("\\.ml[ily]?$" . tuareg-mode))
              auto-mode-alist))

;;; Appearance
(line-number-mode t)
(column-number-mode t)
;; (tool-bar-mode -1)
(global-linum-mode t)
;; (require 'whitespace)

;; Interactively Do Things
(require 'ido)
(ido-mode t)
;; (setq ido-enable-flex-matching t)

;;; Programming

(setq-default indent-tabs-mode nil) ; Because tabs are evil
(setq-default tab-width 4) ; If someone else uses tabs

;; C/C++ mode
(setq-default c-default-style "bsd")
(setq-default c-basic-offset 4)

;; Haskell (supported by default by Flycheck)
(add-hook 'haskell-mode-hook
          (lambda ()
            (haskell-indentation-mode t)
            (inf-haskell-mode t)))
