;; OCaml configuration

; load tuareg
(load "/usr/share/emacs/site-lisp/tuareg/tuareg-site-file")
; opam isn't installed, explicitly give the path to merlin
(setq merlin-command "/usr/bin/ocamlmerlin")
; enable merlin whenever entering tuareg
(autoload 'merlin-mode "merlin" "Merlin mode" t)
(add-hook 'tuareg-mode-hook 'merlin-mode)

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

;; autocompletion
(require 'auto-complete)
(require 'auto-complete-config)
(ac-config-default)
(setq ac-show-menu-immediately-on-auto-complete t)
(setq ac-auto-start t)
(setq ac-auto-show-menu 0.5)
