/* PW3-OS original e-ink puzzle pack: memory match and Sudoku.
 * Reuses Inkwell's MIT framebuffer/input abstraction, but NONE of Inkwell's games.
 * Source has a host-only logic test and an ARM/e-ink UI build.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static const char *sudoku_puzzle =
 "530070000" "600195000" "098000060" "800060003" "400803001"
 "700020006" "060000280" "000419005" "000080079";
static const char *sudoku_solution =
 "534678912" "672195348" "198342567" "859761423" "426853791"
 "713924856" "961537284" "287419635" "345286179";
static int sudoku_fixed(int i) { return sudoku_puzzle[i] != '0'; }
static int sudoku_correct(const char *board) { return strncmp(board, sudoku_solution, 81) == 0; }
static void match_deck(unsigned char deck[16], unsigned seed) {
    unsigned state = seed ? seed : 1;
    for (int i=0;i<16;i++) deck[i]=(unsigned char)(i/2);
    for (int i=15;i>0;i--) {
        state = state * 1664525u + 1013904223u;
        int j=(int)(state % (unsigned)(i+1));
        unsigned char v=deck[i]; deck[i]=deck[j]; deck[j]=v;
    }
}
#ifdef PW3_HOST_TEST
int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1],"--selftest")) return 2;
    if (strlen(sudoku_puzzle)!=81 || strlen(sudoku_solution)!=81) return 3;
    for (int i=0;i<81;i++) if (sudoku_fixed(i) && sudoku_puzzle[i]!=sudoku_solution[i]) return 4;
    if (!sudoku_correct(sudoku_solution) || sudoku_correct(sudoku_puzzle)) return 5;
    unsigned char d[16]; int count[8]={0};
    match_deck(d,20261110u);
    for (int i=0;i<16;i++) { if (d[i]>7) return 6; count[d[i]]++; }
    for (int i=0;i<8;i++) if(count[i]!=2)return 7;
    puts("RESULT: PW3OS_MEMORY_MATCH_AND_SUDOKU_LOGIC_PASS"); return 0;
}
#else
#include "ui.h"
static unsigned char deck[16], matched[16];
static int a=-1,b=-1,turns=0,win=0,selected=-1;
static char board[82];
static int sudoku_mode=0, status_message=0;
static int button(int x, int y, int w, int h, const char *label) {
    fill(x,y,w,h,WHITE); frame(x,y,w,h,2,0x55);
    text_center(&f_ui_bold,28,x+w/2,y+h/2-15,label,BLACK);return 0;
}
static void draw_match(void) {
    int top=180, sz=(W-100)/4, gap=8;
    fill(0,0,W,H,WHITE);
    text_center(&f_ui_bold,55,W/2,45,"Memory Match",BLACK);
    char msg[100];snprintf(msg,sizeof msg,"Turns: %d   Matched: %d / 8",turns,win);
    text_center(&f_ui,35,W/2,115,msg,BLACK);
    for(int i=0;i<16;i++) {
        int x=34+(i%4)*sz, y=top+(i/4)*sz;
        fill(x,y,sz-gap,sz-gap,matched[i]?0xDD:0xFF);
        frame(x,y,sz-gap,sz-gap,3,BLACK);
        if(matched[i] || i==a || i==b) {
            char v[2]={(char)('A'+deck[i]),0};
            text_center(&f_ui_bold,72,x+(sz-gap)/2,y+(sz-gap)/2-34,v,BLACK);
        } else text_center(&f_ui_bold,52,x+(sz-gap)/2,y+(sz-gap)/2-28,"?",0x66);
    }
    if(win==8) text_center(&f_ui_bold,42,W/2,top+4*sz+20,"All pairs found!",BLACK);
    button(35,H-148,W/2-52,92,"New game");
    button(W/2+15,H-148,W/2-52,92,"Exit");
    flip();
}
static void draw_sudoku(void) {
    fill(0,0,W,H,WHITE);
    text_center(&f_ui_bold,55,W/2,32,"Sudoku",BLACK);
    text_center(&f_ui,28,W/2,100,"Tap a square, then choose a digit",BLACK);
    int tile=(W-40)/9, ox=20, oy=174;
    for(int i=0;i<81;i++) {
        int x=ox+(i%9)*tile,y=oy+(i/9)*tile;
        fill(x,y,tile,tile,(i==selected)?0xCC:WHITE);
        frame(x,y,tile,tile,((i%9)==0 || i/9%3==0)?3:1,BLACK);
        if(board[i]!='0') {
            char v[2]={board[i],0};
            text_center(sudoku_fixed(i)?&f_ui_bold:&f_ui,39,x+tile/2,y+tile/2-19,v,BLACK);
        }
    }
    int by=oy+9*tile+40, bw=(W-32)/9;
    for(int i=0;i<9;i++) {
        char digit[2]={(char)('1'+i),0};
        button(16+i*bw,by,bw-2,74,digit);
    }
    button(20,by+110,(W-60)/3,90,"Clear");
    button(30+(W-60)/3,by+110,(W-60)/3,90,"Check");
    button(40+2*(W-60)/3,by+110,(W-60)/3,90,"Exit");
    if(status_message) text_center(&f_ui,32,W/2,by+235,status_message==2?"Solved!":"Keep going",BLACK);
    flip();
}
int main(int argc,char **argv) {
    sudoku_mode=(argc>1 && strcmp(argv[1],"sudoku")==0);
    if (fb_open() || fonts_load()) return 1;
    input_open();
    char *seed=(char *)sudoku_puzzle;
    memcpy(board,seed,81);board[81]=0;
    match_deck(deck,(unsigned)time(0));
    if(sudoku_mode)draw_sudoku(); else draw_match();
    for(;;) {
        event e=input_wait(60000);
        if(e.type==EV_POWER) return 0;
        if(e.type!=EV_TAP)continue;
        int x=e.ux,y=e.uy;
        if(sudoku_mode) {
            int tile=(W-40)/9, ox=20, oy=174;
            int by=oy+9*tile+40;
            if(y>=oy && y<oy+9*tile && x>=ox && x<ox+9*tile) {
                int col=(x-ox)/tile,row=(y-oy)/tile;
                selected=row*9+col;
            } else if(y>=by && y<by+74) {
                int digit=(x-16)/((W-32)/9);
                if(selected>=0 && !sudoku_fixed(selected) && digit>=0 && digit<9) board[selected]=(char)('1'+digit);
            } else if(y>=by+110 && y<by+200) {
                if(x<W/3) { if(selected>=0 && !sudoku_fixed(selected)) board[selected]='0'; }
                else if(x<2*W/3) status_message=sudoku_correct(board)?2:1;
                else return 0;
            }
            draw_sudoku();
        } else {
            int top=180,sz=(W-100)/4,gap=8;
            if(y>=H-148) {
                if(x>=W/2)return 0;
                memset(matched,0,sizeof matched); a=b=-1;win=turns=0;
                match_deck(deck,(unsigned)time(0));
            } else if(y>=top && y<top+4*sz) {
                int col=(x-34)/sz,row=(y-top)/sz;
                if(col>=0&&col<4&&row>=0&&row<4) {
                    int i=row*4+col;
                    if(b>=0 && deck[a]!=deck[b])a=b=-1;
                    if(!matched[i] && i!=a && b<0) {
                        if(a<0)a=i;
                        else {b=i; turns++; if(deck[a]==deck[b]) {
                            matched[a]=matched[b]=1;win++;a=b=-1;
                        }}
                    }
                }
            }
            draw_match();
        }
    }
}
#endif
