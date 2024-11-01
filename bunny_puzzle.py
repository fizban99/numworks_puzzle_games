from kandinsky import fill_rect as fr, draw_string as ds
from numpy import  zeros as zs
from time import sleep as slp
from ion import *
import random

const = lambda x: x
_ID = const("int")

FG = (0,0,0)
BG = (255,255,255)
_BLNK = const(15)

class TP:
    def __init__(self, w1, w2, w3, ll):
        self.w1, self.w2, self.w3 = w1, w2, w3
        self.ll = ll

        self.m1l = self._cmv(w1)
        self.m1d = self._cmv(6 - w1 if w2 > 0 else 7 - w1)
        if w2 == 0: return

        self.m2l = self._cmv(w2)
        self.m2d = self._cmv(13 - w2 if w3 > 0 else 14 - w2)


    def _cmv(self, w): return (2 << (w - 1)) - 1 if w > 0 else 0



class SW:
    def __init__(self, ws):
        self.ws, self.idx, self.of = ws, 0, 0
        self.buf = zs(ws, dtype=_ID)

    def reset(self):
        self.idx, self.of = 0, 0

    def add_b(self, bytes):
      for b in bytes:
        self.buf[self.idx] = b
        self.of += ((self.idx + 1) // self.ws) * self.ws
        self.idx = (self.idx + 1) % self.ws

    def get_b(self, d):
        return int(self.buf[(self.idx - d - 1) % self.ws])


class TI:
    def __init__(self, p, z=1):
        self.clrs = [
            r565(next(p) * 256 + next(p))
            for _ in range(next(p) + 1)
        ]
        self.sw = SW(2047)
        self.z = z


    def s_img(self, data):
        img = fb64(data)
        w_l = (next(img)<<8) + next(img) 
        self.w1, self.w2, self.w3, self.ll = w_l >> 13, ((w_l >> 10) & 0x07)+1, ((w_l >> 7) & 0x07)+8, w_l & 0x7F
        if self.w2 == 1: self.w2 = 0
        if self.w3 == 8: self.w3 = 0
        tps = TP(self.w1, self.w2, self.w3, self.ll)
        self.img = dc(img, tps, self.sw)

        dims = (next(self.img) << 24) | (next(self.img) << 16) | (next(self.img) << 8) | next(self.img)
        self.w, self.h = dims >> 18, (dims >> 4) & 0x3FFF
        self.swapxy, self.dr_ln = (False, self.dr_lnx) if dims & 0x04 == 0 else (True, self.dr_lny)
        self.w, self.h = (self.h, self.w) if self.swapxy else (self.w, self.h)
        type = dims & 0x03
        self.gcl = self.gcll if type == 0 else self.gcll2 if type == 1 else self.gclp

    def gcll(self):
        clrs = self.clrs  
        yield from ((clrs[b & 0x0F], (b >> 4) + 1) for b in self.img) 

    def gcll2(self):
        clrs = self.clrs
        while True:
            try:
                yield clrs[next(self.img)], next(self.img)
            except StopIteration:
                break   
    
    def gclp(self):
        clrs = self.clrs  
        yield from ((clrs[c], 1) for c in self.img)

    def dr_lnx(self, x, y, lx, ly, c):
        if c != (255, 255, 255):
            fr(x, y, lx, ly, c)

    def dr_lny(self, x, y, lx, ly, c):
        if c != (255, 255, 255):
            fr(y, x, ly, lx, c)

    def dr_img(self, x, y):
        if self.swapxy:
            x, y = y, x
        x0, pc, tl, z = x, -1, 0, self.z
        for c, l in self.gcl():
            sw = l * z
            if x + sw > x0 + self.w * z:
                if tl > 0:
                    self.dr_ln(x - tl, y, tl, z, pc)
                y, x, pc, tl = y + z, x0, c, 0
            if pc != c:
                if pc != -1 and tl > 0:
                    self.dr_ln(x - tl, y, tl, z, pc)
                pc, tl = c, sw
            else:
                tl += sw
            x += sw
        self.dr_ln(x - tl, y, tl, z, pc)


def dld(od, eb, tps):
    if od & 0xC0 == 0x80 or tps.w2 == 0:
        d = (od >> tps.w1) & ((1 << (6 - tps.w1)) - 1)
        l = od & ((1 << tps.w1) - 1)
        return l + 3, d + 1, 1
    eb1 = next(eb)
    if (od & 0xC0 == 0xC0 and eb1 & 0x80 == 0) or tps.w3 == 0:
        cv = ((od & 0x3F) << (8 if tps.w3 == 0 else 7)) | eb1
        d = cv >> tps.w2
        l = cv & ((1 << tps.w2) - 1)
        if d <= tps.m1d: l += tps.m1l
        return l + 3, d + 1, 2
    eb2 = next(eb)
    if (od & 0xC0 == 0xC0 and eb1 & 0x80 == 0x80):
        cv = ((od & 0x3F) <<  15) | ((eb1 & 0x7F) << 8) | eb2
        d = cv >> tps.w3
        l = cv & ((1 << tps.w3) - 1)
        if d <= tps.m1d: l += tps.m1l + tps.m2l
        elif d <= tps.m2d: l += tps.m2l
        return l + 3, d + 1, 3
    pass



def dc(data, tps, tx):
    of, p =  0, 0
    tx.reset()
    for od in data:
        if od & 0x80 == 0x00:
            if 0 <= od <= 127 - tps.ll:
                tx.add_b([od])
                of += 1
            else:
                ll = 127 - od + 1 
                of += 1 + ll
                tx.add_b(next(data) for _ in range(ll))
        else:
            l, d, nb = dld(od, data, tps)
            of += nb
            tx_l = tx.idx + tx.of
            ep = tx_l - (d - l)
            if ep <= tx_l:
                tx.add_b(tx.get_b(d - 1) for _ in range(l))
            else:
                ch = [tx.get_b(d - i - 1) for i in range(d)] * (l // d + 1)
                tx.add_b(ch[:l])
        tx_l = tx.idx + tx.of
        while p < tx_l:
            yield tx.get_b(tx_l - p - 1)
            p += 1

def r565(c): return ((c >> 11 & 0x1F) * 255 // 31, (c >> 5 & 0x3F) * 255 // 63, (c & 0x1F) * 255 // 31)

def gclr(p):
    p = fb64(p)
    return [r565(p[1 + i] * 256 + p[2 + i]) for i in range(0, p[0] * 2, 2)]

def fb64(eb):
    base64_index = zs(128, dtype=_ID)
    for i, ch in enumerate(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"): base64_index[ch] = i
    dl, ai = (len(eb) * 3) // 4 - eb.count(b'='), 0
    for i in range(0, len(eb), 4):
        bi = (base64_index[eb[i]] << 18) | (base64_index[eb[i+1]] << 12) | (base64_index[eb[i+2]] << 6) | base64_index[eb[i+3]]
        for byte in (bi >> 16, (bi >> 8) & 0xFF, bi & 0xFF):
            if ai < dl: yield int(byte); ai += 1

def cur(c, pos):
  fr(pos[0]*54+3,pos[1]*54+3,54,1,c)
  fr(pos[0]*54+3,(1+pos[1])*54+3,54,1,c)
  fr(pos[0]*54+3,pos[1]*54+3,1,54,c)
  fr((1+pos[0])*54+3,pos[1]*54+3,1,54,c)    

def move(vx, vy):
    global pos
    global solved
    if pos[0]-vx<0 or pos[0]-vx>3 or pos[1]-vy<0 or pos[1]-vy>3:
        return
    new_x = (pos[0]-vx)
    new_y = (pos[1]-vy)
    new_index = new_y * 4 + new_x
    pos_index = pos[1] * 4 + pos[0]
    clear_tile(new_x, new_y)
    tile = tiles[new_index] 
    img.s_img(data[tile])
    img.dr_img(pos[0] * 27 * z + 3, pos[1] * 27 * z + 3)
    cur((255, 255, 255), (pos[0], pos[1]))
    tiles[pos_index], tiles[new_index] = tiles[new_index], tiles[pos_index]
    matches = show_matches(tiles)
    pos[0], pos[1] = new_x, new_y
    if matches == 16:
        ds("SOLVED!!!",226,10,(0,0,0),(0,255,0))
        solved = True                    
    
def show_matches(tiles):
    matches = 0
    for i in range(16):
        if tiles[i] == i:
            matches += 1

    ds(" Matches ",226,50,FG,BG)
    m = "0" + str(matches)
    ds("   "+m[-2:],226,70,FG,BG)
    return matches


def clear_tile(x, y):
    fr(x*54+4,y*54+4,54,54,(255, 255, 255))


def shuffle():
    numbers = list(range(16))
    shuffled = []
    while numbers:
        k = random.randint(0, len(numbers) - 1)
        shuffled.append(numbers[k])
        numbers.pop(k)
    return shuffled    


def is_solvable(tiles):
    inversions = 0
    for i in range(15):
        for j in range(i + 1, 16):
            if tiles[i] > tiles[j] and tiles[i] != 15 and tiles[j] != 15:
                inversions += 1
    return inversions % 2 == 0


def draw_tiles(frames=True):
    for row in range(4):
        for col in range(4):
            tile = tiles[row * 4 + col]
            if tile == _BLNK:
                clear_tile(col, row)
            else:
                img.s_img(data[tile])
                img.dr_img(col * 27*z+3, row * 27*z+3)
                if frames:
                    cur((255, 255, 255), (col, row))
    if not frames:
        for col in range(5):
            fr(col * 54+3, 3, 1, 54*4, (255, 255, 255))
        for row in range(5):
            fr(3, row * 54+3, 54*4, 1, (255, 255, 255))



palette = b'P9yS1DHUUuX39tvNdP/f5RTks+1V5x7FPtYdrFqK+qQ+tL5yFoKYWXCDFUjMvVpqE4EOm92TfJs4w/YgZanR0rP11/ZY9BOze761v7WvU57TlnGGEXWwU4yOb0PqbW51rkrLZQ580GQuTExUrTJpO2qVs5zWpJF7j34O39evUJbP'

data = (
b'UHcAe2wBsgABwBMCwXGAxrjDSALGzADCJMKnxCYApaybAsLkksakwqPD5tKlwiXC5MoHxiXDiMZCAwTUIclkj8aDBQQGBsajwmfGgwMGgADGRtPnAcZAw0PDCcNCxmLDQcMFgsMhB8MjzWDDCMnJw0TCYcMmCMMkBsKDyenNJNDDwALVocnnw0gABwMDA7jDJcNBw6MABb4Hw0qDz6QE0KYGCAAAAH8JySADzEXNRsNCCAAICIymmoPBI8JHwAIHxaXAocQoB8JKygLDpQfMoLvOIc2Etw==',
b'LOIAfGwBsgHAgCACwK4SwVICwHGLAsNowgKAwFLDJMJlwAfGN8M7AIYHB8g0mcAIBsACAwPGMgDAE8AhBgYKCwyACgQHAMJBygcGBg0ODw8PEBALDAMAgcNmBgYREre4EMNCyjOEBgYTE8M1EAwJxxKwzTIUFcMzymIDCAgACMNizTATwzgQDMMD0GEWFxjDNroLwzTaMBEYxnIZrocPC9hgwyPGYbYSGcMBgA23CLUGFBO3ERIauMNhDcowwyIMEcMxF8pAwAEPGQsIgOgSDRe3FRfHAsABt+tTGxcTFcpFgxkZHNtwzhIIFLaBFxEOGsABGQfNcrvDNhLDMhrYI85BFBHDMR0VEREOgRoNyVHDMhzDMs4Sw0HNEuohxwHKQh3YYBESug==',
b'MF4AemwBsgECAcAVw0HAhsMpxtYCt8PilMNLwAHA5cyFhcAOwyLDD8dCwMEAw7LDENKGx0DDr9Qrw6/KYcAkzCuSAKqHwQLAQcLCwYLHYsABCMCECAMEwiLFpssFCQQKDMNDw8LJZQgECgsQEMNHwAUJBgwQEBAPywAIy2DAQcxiAADGQrTCAs9lgwQKrIHGYMagwuTMwcmAwyEas8OEsMMlGg4Sw0PD4sZgC8ZDDg4SFwgIB8LBwKIEC68ZxkARGBjCwsMCCAkKsRkOEhIYGB4erMLjxEAKrsZBF7MeCQkHCYEHgASwGRrJYbMfGwkgggmLIRDGRbMeHw==',
b'TNwAfGwBsgHAgEwCk4Wym8JSwxUBAgLDAsJlwUHCYomTucADsgCvAICQnqLJYstkzWXHKNJExDTOZ8YExETEc8YmAAAICAMhAwQMDAwNHAfNIoMCAAghBgYMCxAQD4LDKAACBgwQgcMCGg4cB4AIwAHCdhkaDg4SHMkSzWTDAMMhwnERERfaJcMjxgQOFB4eHhfDBscxyRTCcB4fGxzYVYLJIh4YwwAiHxLQQcAEEhLDAR+BG9NywyjGEsMSGwgI1wDDJxjGJB8cEtkg4yDABMYkHx/dY4EJBwmCH8MjIxIcySTDAJGAxiMbEsxg0EsHB8ZCEg7IVsACxlMbEhvIIMJayDI=',
b'LEcAfGwBtgfAAgnAYgWBIMABISEIgQcIryQmJycnKCkqLjF+Ogm5AK7BsSQmsikpsi4xNTQyAyDDUwgHBSUlKCkurC4xgDU0NC1/OsNQgSSyLsGRwaMtLTczCLeyxJAqMMNUNTXBsbPE0CyywbLBojU0N8GhJSUnwZG2NcNVNMNSw0DE4cABNjTBsjQ0NDcIAAfDRC7BsTMzxQQ0LQDDQc5wwAHKETM2w1S0JMaWy9M1MMNUyEkvzWQ2K7PDUMGkscGzMDDDViorLYKBNzDAATYVMDYwwaLVYNWRMioygDExMzAwMzMrxQfKFMUCK8iB1AHBosnwwbI1MNDyNc1xJyjDWC41zYLIcNKA0nDNZSonDAoWGQ0y2xE02UAmJSbBssvgOAsLCwwPDw4zw1PSli4uNDB3OQsQEAwZGhIrw1LIgMNjLjMzyFAyfTkaC7YdHeACJSUmxOAqKzMvLy4WCxAZDRAZEhMt4ALZcMNwLjHG0BbGwA0cDRoOfzvUMOUSJcbwxSEvDAsMFhAaC7QxwaLoYbgoKi4Mw1AQGQwODjIh',
b'LEQAfGwBsgjACBwUExUVFR0VFRcREg4OwanBwRPBsw3BmgmAHBfDoBMMBgqeB8GIgQgcDAYMCwvDBgfBhAkJILELEMGawFEDCq7BpcLTsIQDChCyEBDBoQfC08GBICEKEBuuwaLGVgcgISEhBg0dHcGyBcGBw3OwIQQLEBLDQxAkxKizCsFzDxAPJssFsSHGgMAGJsNjwxKEDA4VHR0XwzHDUCTEwcGCyDAQ1dAdHQ7BosUQxMDDEcNBFzsGOcNgsA8PJyfGZbIEDxXBo4EkJ8Fjw1EGDx3E8DsdE8GhCyTDNYAMD9rAgMGjA8GWBAsPDcGhxQPBosniIAQZDxAUtxcZEAwWCxDBoQzDUxkZGQrh4BMZCwkiCSINEBAMIQ0MCwQhIMGhGQo5ORsQCiIiIhwMgAMaCwsDBMwwGhkcIhwZDxkLCgo7HAoSEhshDRkZ3xDFkBojwtAjGRkLFgo7CgobohQSDxkZDcbAEA4jHBsaGRkQO4AWx+EXERESEtDBAw4ODhq0xREKCrIFHRQcBcvBISAaGRoOGbcZEBAL',
b'LEUAdmwBtg4LDAsLCxDAAw+AGRAKCgYKMAoZILLBiLcMCoAMGSAECxDBsg/BwhkZwbELGRkgCsNbDrK6icNXw2APFR0VFRUUDK7BocM1EBAaHRYEHR0dExQKw6AatAzDQhrE4BV9OwYGtB0TOcaQCxAgIQyzDh0QEBkdHX47O7UVE8UgCw0JIAq1Eh0ODxetNjbBoiMMGgnGwcgAHRcPGrXFAhQLHCK0A8vCzrIdFcGRw0AWIiILGscCw1C5FKwVFRMTAwwjIiIcGhkaGg7J0MNjEsTBOQMLGrQMtBIRE8/QwAMTExMRztAaHBzDEA4RFRUXGcNT0FMawAINsxUVG9OjwZgSERKwGBMcHA4OwZkOERERF7IVFyAgFhISusMUwyCAFRiAFAkgICAbEoAOgMFxgLMXHLIgIAMNwTPAARsDwaHDQYEhHMHUDQMhIRgYHsTzwAQhIaqAICEeHh4XHAmgwWGCuYAtKzq0EQkJCQYEwZGAOgXBoTMtLbQUB7TBYbo6KysrwcE6LR8eEhwHBwkEw1HAATotKys6twMeHxIHAwYGBgTIpiE6MzfBsQ==',
b'LEQAeGwBth8SHAMGgAQgwAUhISEFO4ofEgeztTqBtYIDOjs7EhzBoiEFNystLTc3NwWoOgUDOiEhEgcJwaEDBSs3KysyOgXFQzvDoBwHCQTFAgnGxyA6M8VhBwkJwbHIaDsrN7MFB7chBAQEjMGBBSstNwXKQS2iCQkHB8NSCYIgMysrssIRwZIgxrDDUIPL8iAhMyszwaIHBCHBgsVDw1EFIcGjxxGBtyHPY7WztwMkJCYnJygpMjg4A8OxwZUFJCYmJrAqKi4xNTUyAyHBpAkkJSUoKS4qLi4uMbI1NDQyIcaDBSUlJymvwaG2NC0tM8GhsyoqKjPBwcGhNS0tLQkItCUlJinGQDMzwaPDYwcHCLPH4bYwwZS3w0ADJSXDMcGxNsUFNDQtw0InKMGSy4Aww1Q0NDTJ4Mthw1PLwCowNMGmJMNJgDArxQW1xpTDUYAzNsGkxqbBgshhMCvE8MGiKTIqgjIxMTMxMzUzMzQ0HTA2NjbBoivdsMAEMIA2NojFCMhkxQA2K8ax',
b'KEEAfGwBtiGAICEgAyYoKSouLjE1gTQ0NTkMCwuswAEmJyouMTGqNC00LYAyELXA4SQmLsGgwN03LTc5waQgAycpsjGytoE3McDLwonBqTQ0MgE7wak3Ny0zwNTBsMJ4NTQHIiIzLcKaN8DdJCcuxOk7tMKRNDQ3NwXA1CrFzDM2NrcxwqDAyygxMjo6M8aqNTY3Ni0vtDqzJygxMcMwIjKwNLwrNjO0wbEkJyoxMQm0OisrojA3NjYvxTHBsMaoLsKBOsNqKzA2NzQ+wNLGoceJxDk6OzA3xCg1tDY3MshRwNQ6xeQpLzaAMDs7MDswJMTowmjDgMlRNzcrMDC2MyuAMj0ptclBtCsrMzQ0MDcyJykpKioqKSUlKMlRsisrLSg+KSk4MjIqtS4uKSYmJinL4SvCeD4+KiQnMTAwM8GgxDkkJSYnJy7K8Dc1PsUINDgoMjYzL8ULKj0nJyg4KjMrKj4+xrA4JygzKy7A2cQ4KCTRMCkyMiszyIg7O8UIMDArx5Q1KigmJ8PYMTY2AyXFACkpNcZBgMDpMjiiNzMhwRjBIMKBqCvIGTfHojMhwNE8w1UzytDAAwMhA8GrKsJ5NsKagcTwIcDRMSswKzAzxCs1NcR4MTEpKQ==',
b'LEIAdGwBsiEhIDsJICEgIYAEIQQbEg4aGhoZwAEhITAFIMGBsiEgAxsbEcHEAwU6wyDDZIkbERHBwRoaJjAmJiYkwXKyBAYGFra6DhoyMSgouQPFMwaBFhTB0TYqKScoJ7q5wZKAChEXERErKSczKy4pKigmJyQhwZQGBhITExUyMjA2MykpKsHBPcGlGxIRFzMrKzEqKcABKicnJcGkCyMSEi4uLiqAJiiLKScmwaUjI7S4JiezgCjBs7UxMTEuLiYmqi8qKsQAtwoQEBAMtDUxMSYmKcPCLi68KCQGDLS2siglJjUxNZDFwyc9DA8PEBAPCzU1LiUmKTXAASkuuyoptIAMNTEnJyc0wYEow5DDcjgZshAZNTElJyo0NTQ0KMUwgLkvObAZD8NBsC7DIDSBty8XERoPCxrDQCk0NDEnKQquLbkxMTMTExMSEhExJCcuLTQnLjU4LYDBwTU7tM8gKCgoNy0pKgazN4K5shUbIyMnKS43MSg0MTQ3wAPBoxEjIyYqNTcoKsF0NzQqLzwvxQAVFcUALi0uKCguLy88JiUmJnA+Pj4lPj44ExUTFRcjKTEm3+Cgg4WBF8NQFRI1NX0+KSjBAsAGKbUTNTQnMsGcxSC0FQ==',
b'LEgAeWwBshkZGhmHDRAaGg4REREXERYhgDMtfjohrxoaEBkODhsbtRENs7Y3Ia6ADhsaEsMQFBIXDAYEwbIFfzqvDhISERsbxLAXFw0GgCEhA7fEMcABDhIRFxMTERu0BCE3MwUhIcGUExcXhBEREsNxBDMrthUVFRMVE4GvEhIODrcDKzcrIcYBwvSux4HBsSF9OjIhyBCCEhEOrMxhtMGyISQjIxsOIxojr7PBscbxBCYmI8ACwaTDQbYMCiYmLMGBCwwLDMNVwdESJycpKrAMDAsQDw/TAsNUDhIOKioqwxGwssNItjIqLiMMrrHIRrESEhQuLgzDIcM1CwwGCgwLwcERMi4GGRDBcw4PCgwQEBAPGRANxrASFCTJkbLOgQquxBLYswwbDA4ZxbERFwrI58GhIxsbEhIe1HAUFsj1yNPToLYbEoYbs8qB0TTfQBvUQIQbGwrBlswiERGzw4ESDMGFw0LHwLDDQsGhwYLUU8NQw0IbEh4W2UXDQ8NRw2HIcBIUC8M5w0ASE8Mxw1ESG8FhwZO1',
b'KEAAc2wBsiE6ISEhMy0zISCOIQMzN4AtgDY2LSEFISE6LTqzAyQmJiY1t4A2NjfBUAXBwSGvJiYlJjHA1wMDwkmvJycpKSgpKcHBNrQ7OsKIITorKScnKK6ygDU1NDYwMiE7w+ErKykoNcCpwAQwOye0AysrKy4oNCqgPKuIKikrOyghOyQmMTUxKCo0wXTBCDyCMDsqJismKCgrhKQuK7MqwAEwMLQoKS41KS4tsjcpKjzAuS4utC4pwkA3hC4pKjYxq66BtTIqwaA0uzXBccACMbXBaDUuwYE1LbAxwAW0NS4uLS40NyoqNsFhgDXAAjIyJysuNS0uNjUuNzTAqzo6NTQ0KSUlJyg3LjQ1NDcuNTfAwTQ0NAkJOjEnJirB+AYGBDg3NTEtwQCFtAc6Jzg6wtEMDAoKFjE1N60tMwIBMjoiAgUiBzrCEAsLuDgtLbMtMgciIiIhCYgytBALuBY3NC2yLS06ByIgAwQiOjPC0SO0CwwrLSst0KM0IiAHAcFDwNSztivCYCIiAJ60wokLwZqBOyIiO4fBUMDTy4jSUysCOr47wFkjwokWPsADJj4+Ly8uLsILtBAjJMDUwAY/Ly8jgMGmPig4J8A5JzgoPj4=',
b'KEAAd2wBthALEBAQDYAbGxYOEhQUFxcXExcTExM5MTELFgyAFsDZFIHA3DgxCwvBsLAWC8ESFhY5FBQ7OxQkJzExPSQWFsDiDRvBwsGpEz0uLrQmPyc4Fg23tcNrOSm1JSU/gSg4OYDDcsGoOTGyMSU9wNGALCwsKCwpKSkrKzY4KbU+wNQsLDwsKTQrNoEzJMKBPsNgrrXAuYaEMzjA0cNiLDE3gMJYwAE3MDs5JzE+JsKILzStwLkrNS44ORQRFxe0Pj0xKzczKzMrNy01LsRIOMiRERcUJy4+Ljc0sjcxrMOIOBuAFBQWORs5MTc0wkguL8XkxsgbGzkWOcewFTM0KyrF9D4sOMhwGxYErhcTw7Apw2DF8T8mPjnJWBYWyHowxIk+tMXyKLIWFsNBOcGRNjcrtMlashbNsbYwNjc2NjQxMD4+P8KJJxYNzns5MTY3NzY3PDHCgrWyzZE5LC7BkCsuPC42NjAuPD4/JT0nFrM4LLIrNjWNMCsrLckYMz0MCw05OMOIL7LH2C/JgCs2MTQ0NCsECxYnxSkvykg8x9ArwZjFGDMzKzU5JMvqP7LNsTOyxTLB4CnF8Sw/NDeytsJoMDYrPDctLS01Nz0+wnOzwnHEKC8xKjE1NTQ0OCbCcsDJKjAyMDA1PDU3',
b'LEAAeGwBsjUyKjI+wAk9FhYWOTkXFRU1MSkpPj4/wYUmEBoODhISEhEREzQtMjzDFzworbGALTQzPMNBPy8vNIAzEhvBchEXFzcuM8LQPzysNbcUwXOANy41Pj+ALzE0KDU0LbgtwAQxLjTE8Lk/Jj48Ly8uwcY9PSQlwZMlJsBxPywsPMIwMS8sPiYlPT27PT2qwbLAUywvLyzB0T3DQqCEwdExMDEsgT8mPbwmxbLBsiwwPMJiwAE+vT0mJj7FEsLxwXLAgz8mxdHD8CYmwXTBwigFwIKwJT3Bd7IJCSjCusAFBQkkBygswcY8LCwoMTIrM8ThBwfDVo8oMTMrMy7A4igFw0A/w3WuKyvDsshigoXK0SgzM88wsDwvPNORwAQ8pjYwNbAxMa+8wXLB4rI8MYaBpzU0w5Y1PC8twZGWNDQ2KzXFSC43LsMCMSs2KzHFNoExwZE8MTfBjC8vwZHBgsAMsi4zNjfGKMAF',
b'cEEAbWwBshUVGxsbEhsSEhQbGw4ODhqYEg4SEhIRFyMVFRURGxsWBgwMDAsMDA3DQcMiERQ5FxMVFRMMEBkQD4AZGRoZw2MRFzc1FxMTEzsQDxoZgxrKIsMgKy0twyATFBkLw0AagsMCESstN4iBMxSFOxczOyvGIMMlwA0xNTU0gy0toTQ0MS88PC88LH8/wBLDosRIxavBoZi0wmXCJ7OKtcTnwkOlgD09PSUmgT4+w+LCgsTiJpkmJyYnJcRgwAQmKcShhjyZPJCAwsjEgMThmMKgw8DGaiwsKMSDOCnHAcKLyAU5OTgpywHSZSwoqsTiOMOALy8v6YCotYU6OcJBmjY1oCoz7wDE4y8ymMXDNzXWIS81Kzc1w6OENjc8wiA2w2EvLyswMDWwLsNDMTc1LZjDIoA0MCs0wyTMgJLE5JArNzfHIcAExaAuiDU3Nw==',
)



z = 2
img = TI(fb64(palette), z)

key_pressing={KEY_OK:0,KEY_PLUS:0,KEY_MINUS:0,KEY_LEFT:0,KEY_UP:0,KEY_RIGHT:0,KEY_DOWN:0}
key_pressed={k:0 for k in key_pressing}

tiles = [t for t in range(16)] 

draw_tiles(False)

ds("[+] mix",226,160,FG,BG)
pos = [_BLNK//4, _BLNK%4]
show_matches(tiles)
solved = True
while True:
    for k in key_pressing:
        key_pressed[k]=0
        if keydown(k):
            if not key_pressing[k]:
                key_pressed[k]=1
                key_pressing[k]=1
        else:
            key_pressing[k]=0
    if not solved:
        if key_pressed[KEY_LEFT]:
            move(-1,0)
        elif key_pressed[KEY_UP]: 
            move(0,-1)
        elif key_pressed[KEY_RIGHT]:
            move(1,0)
        elif key_pressed[KEY_DOWN]:
            move(0,1)
   
    if key_pressed[KEY_PLUS]:
        fr(226,10,100,20,BG)        
        tiles = shuffle()
        solvable = is_solvable(tiles)
        blnk_in_even = tiles.index(_BLNK) // 4 % 2 == 0
        if (not solvable and not blnk_in_even):            
            tiles[0], tiles[1] = tiles[1], tiles[0]
        elif (solvable and blnk_in_even):
            tiles[-1], tiles[-2] = tiles[-2], tiles[-1]            
        draw_tiles()
        show_matches(tiles)
        index_blnk = tiles.index(_BLNK)
        pos = [index_blnk%4, index_blnk//4]
        solved = False
    slp(.2)