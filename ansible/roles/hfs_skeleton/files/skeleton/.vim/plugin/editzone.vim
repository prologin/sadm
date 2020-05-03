" editzone.vim
" Parameters related to the edition zone

" Display relative line numbers and absolute line number for the current line
set number relativenumber

" In insert mode, display absolute line numbers
au InsertEnter * :set number norelativenumber
" Come back to standard mode when leaving insert mode
au InsertLeave * :set relativenumber

" Default status line
set statusline=%F%m%r%h%w\ [FORMAT=%{&ff}]\ [TYPE=%Y]\ [ASCII=\%03.3b]\ [HEX=\%02.2B]\ [POS=%04l,%04v][%p%%]\ [LEN=%L]
set laststatus=2

" Disable bells
set noerrorbells
set novisualbell

set colorcolumn=80

set textwidth=79
if version >= 703
  set colorcolumn=+1
endif

" Show special chars
set list
set listchars=tab:.\ ,eol:¬,nbsp:␣

" Highlight the screen line of the cursor
set cursorline

" from : http://vim.wikia.com/wiki/Highlight_current_line
" toogle highlight cursor column
nnoremap <Leader>c :set cursorcolumn!<CR>
" toogle highligh cursor line
nnoremap <Leader>l :set cursorline!<CR>
