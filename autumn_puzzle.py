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



palette = b'D7ww3RJqq8NKSafl5ptt0+7mm82ZzVU445ppnFJxx9Ht'

data = (
b'CJcAc2wBtBAoCQoAMQoBCgmCCikKCBkBWFkKGQgJKEkIAkhJGDlIKQgJAgooCl0KOQpdIgMCOAkKDQANBgwiDCIGPAMCAgQBCRFDXC4sAwwEAgQLIhYMAgweDC4DLCMCBAYNBQEAHA53jAMGAgwTBgQMxhgFCQAzDC4CDAQLHgMHA6IJDQkIBQYLAgEDBmMXAwcGBAIKAAooBQQDDAYHHA48BgcBwRGlGAkNAgYVAgATBwEXAQcAEgoIDQooGQgEAxUMBhcxABIACAkNCg0oDRgWDAUCBgEHCiEGDRkNCgkCGRgNCA0DBwIFAgcRzhAGGh0YBJEIiwsHAwUKDQEKARgJGMYYAgQCGA3GYAQCFwENCQEJSA0CJAsJGAIKCAIEDQIJAApYDQIOAAEJEhgNBggNBgQOAQlYCRIAAQAGDQQKGAQJHcpIaA0GCgkaEAQCCQgdlxsESAoCDQnGWBEACw0IHQYSBA0KylAYHQgJOhACCwAIAgYNFCoACdNYAgjXMAoRBgQGxwANCwQaABEAJgQCyWABCgACBAANAg0UCgnGcAETAhUSCBkA0VAtBsQYxwAZFRMFAwQaINNxDQILBgoZ3RABBgo1BAYguh0GxzAZGik=',
b'CLoAYWwBtAQCARUDBBYAAgsACQ0ABAYZCAkKGQABAQsEBgSDAAIEAQkQAgYKKQoJGhANAg1ABAIKGQoCBqUYCQABCgkEDQoHAQANEgkIDQGWCAopGAkKCQEGAhEZAgYBCQ0JFpMGHQopEQAFBg0KCQINCB0JDQYKBgQODA7EYgAKBQECCpcGAhoCESYDBQcSKQEKBQkEAgC5GAIHEBIDBAMFAMZIxUgEAAIJCB0YDQoAJgQ1AxIZEQa5Ag0JCAkBEAYAAwIONQQdEAoBBhoBChgZQAcOBBUNBAAMBhACBAIhCT0BIBfHIA4WMBUCAQUGBBIOBAYBrQcWQMcIFgUCAzUMBAJ4YAYgAQAJBQbBaUUEDUAHAQoBACkFAwJ/hdEAEc8h0iAJGhUEAgN0ZQIGAAEJATlIFQYCgSUBCgQAyikYGX9IzSDDOQIEEgQOGZM5V0gFAwcICjEaARk9ChlYAhUqGQEZChkaEB0ALQoNCgsUAg0BCggJKAk40wDDAQgJzzAGBA0YCg1/yNkwBQbRSAQCGAAGDRkNwXkNAB2VRQEEEQkI1UgBGjgKGQcGBEXZaBoNBjoJCBktAgQGBUUJFsgxDckoCNE4CwQMAyU=',
b'CKgAYWwBsAUEBQEVDgNBBgQLAgAhCgEJCgEHBQYCAQ0CAweMCQYEDAARAAYaAQgKFBUEAgQDFwEKAQoEAgAWAgwHlAgCBAYVCw4TBwEHIQcABgIGByEKCAoLAAEBCwIXAwEKCcQgEQp+cQrFEQsNFwEdAg4CBgABGSGwChEGDgQCDRIEkYMEAlEaAZYGARiuBgwQAgcBBgIxCg0GQQEJAgQOHCYCBMQoBiEJkjEJyhBXAQYMyBjLMQIHIQgaBAYBR8QICgjLQBoxyDgJCAkCDgwDF4QGACoNGAAhGQo4CgIEGw4MDgQLxxgZAgEKIQINGAYIzkgLDgYXAAQBtAQAzDgADRgCCAILBtBAAwECDgEZxCAMzjDBMQkGDCMAAgQQAQYLBB4MAAcKAQYYDRgKAwIeAhYQCg0UDgYDBgCBGBoICRAWCs8IAMcwAycGhAYBCg0CCQAGHBYQzEjTUAYEDgCvBQENBLIcBhAKlwIABwEQAQAUAgUKDdZwHBYAERkdBEIEDcQIqAIABgzCQggZBgkAAhQOAg4ODJfESM5QGgk6Dc8YDhsEDgMEAQ0SBgAMFgAJGhEKDT4UCw4DDAXFcB0MFt5p0lC10HILwUEEChbFQBoJCgAKAAIeDB4ECwwA4QHEEAYDATkAyGgeOwQ=',
b'CJAAbAFwsCECBAZRNwMHAw8TBzEKAQAEAgsMQQgBFwETDyMXEQwODAYMAQ4AMQohBwEHIw8nBhcWAgYBAhEaARoGDBEXAwcjAhMHtQYQCQoJAQoCDcI5AQYSDiOVDFECAwfBAhYABw4DBxMxCkHAeRMxBg4ME0EIIQoJGpwnIQEANAMHEQohGgQMAAEnugkBBgSwdHENBAwBBxEHAwYOGcEJDAcaCVEKBA4AAQoBBwMECBENBAYHBBsCBiG9zEABCREDDgIanowCBA4XARcSFA6sAxAHChEJyjABChYBBwAEDAYiBAIXMQowEgAHARfPEBMCFgQLAqMBABYACQ0UAScOCw4EAgcBCg0EAMZgFgIcDQEA0jDKeIUXEQgBARcWLAQbHgwDBwEagxcBCAkKBg4cBgweAgQCFgAWAQDOWAMHCh0cJiweBCsMAwwKMQMRAgYsBgwOLNU4BBMGDgHMSQARFJQCDtZggQYDAMoAABqYBAsErB4cBogAIQIUBgoNAg6LHBYMBA4cCwwGDgcRNhAELhscEwYEDB4MAAIMCQbUCMUgDRsOK8YYA9MhFswQEiABECsOBBsswQkDEAIECw0KAAcg',
b'CNgAYmwBtAkIGQoCBAItBgAICRIGIBEAChEIGQ0SCi0AGZYaIAoJChkBmh0GCg2RBgkICQEKARkaAQkKCxIdCgkGCQoEAgpTOCkYCSgJBC0IHQgNAhYSBg0mAhYdBh0GDQoJDQoIBgIABwEHAxwDAAEABgNGxEjEMAYCAWtcAzwDPA4ECQoGGAILAg5DTBM8AwKMDQt6jANcMwYNiAZ98zMNqwRxM1wDDDIEDgQeDAYIDQQGqA4cDgx7PhYUAhfHeAAHfnMMxFgHDQsUAgYEDQoOEgwGRlMMAwwjAQwECg0CBA0JASMcfiwOFgsGEg0IAQYMBgxDPBMcAwcABBkYDQccTiRODAMXAAQGKBQiHBbEaCcGAgkYCgcGBA4CBh0WyyAGAwADEAcRAgoICSIWAgQLBBsCBgIcBhIUC2o0AhYOAgAMGw4rAgQWAhsEGwQLJAYwog4MpgsCBHg7HgIMBgIEENMIBGkrHB4bJA4DBg4CBA4GBxABCgsEDwwCLqgOBhckDwMABwIAAQoGHgwfBA4MFAwHnAQeFw4EDgEAAw4Lfk8MiQ8HDAIkaT8eGgMEDgMfAwwCFB8HDg8MHxcPDA4M',
b'CLAAVmwBsCoAAQoBChkwAQk4CRECBhUJAAkKCRopChEAAUgCBA4MJRwACgEZCsEpASoJGAoEeFUEDgYAGQopwSEBCRgCBiUGBQECFAYJCIEKABkBBgCIDCUOBgUNDwwLDAopCErBEQ0DBQMCAxWTAgsGAMYYvQoQAg0WDAYlCA0HD8EpyFAJghAZDRJFDQIvDA4GEAEAKgkBKQoTBQMMAgQALwQGIAogx2gIEQAHChgJDgQLowogGgkKx3AZAglICwQbDkAGCsgQGIMESAkvDMsADgQCFgkYGQgZCw0GOB8MDwx+awLHeCkEDQSlDwcPDBvOUAYCDhQOFslQBAoCKAkfz2gvEg4CDgIbAiDBChwOqQYHAgwOAhQMBBsCAQQGlQwODxcPBM5IqQQMFwIEAgQKDTgMHwcPBxzBCQIMDwYDDwcEAgkGCSiqFwwOEgACAMkgDB8SCg3HeE8GHg8XHsowEgASCQ0YGXdfDB8MAgYEGyTEWAigCnZ/DCQCBiIIDQkNzSkBfV8HD8x4DRkICQIECSjZGAAODNJYCwSeKA0IDQQoqAEJHA8HAhQNGcYADQIdEigN0hAODwwSBilIBAIUCgQNKBoI',
b'CJAAbAFwtAYSDQAaWB0KGAkICQEKOQEqCTgZChEGHCIGDQANIBEqEA0CNh02ARANJgIADQEdCg0AFiIGEA0ACgkKCUpiBi0AHTYAPQYtKgEANgwCBhIdOQgZCh0KBl0WHSYMUhYgCgAGAINOeIRLFCwWDAYcgQwWPGY8DjwePAYMBgAsFgMABiYMBmwmHHWWEAEQFgA2IAYAdsMhAQkKEWAaYAYHBgAZCEkaORoJCslAChAGGClIylgIGQgJGCkaAQAJevgoORAKGpJxiAkYSQo5ABq4CUhZABqIkRiiDRIEBAYCDQl/eLYSAAcDQg0aunCICQQAARMLAgwOBghJaAkoAAQGExsKDAatAgYZOAlICQQMBwwEDgQODAMcBAsGDQkYGVgJAgwDDAsjFwMUBg0iHRlYDg4HDCMcFAwOFAIOAgQLJMYoCLcGAgcUHA4Ee5sEDiIG',
b'CJAAbAFwtA4EDhcMDgQeFA4Emw4ECwsOAgMRBwQOHA5w6xsCBAABBw4EBgwOFCsEixsOAgQCBhQMHls0GwQLBA4LsRsEHB4Ee3sOBCsExDAEO8AhfasUDpwkngsOBHZ7BEsbAgYMPgQOjTsEOyQOGwAGHB4sK6NLBC4cGxYcBgwGnRwODA4MHgQrAwyZVgsDHlwOHC4GwGomAAIODw5LAiwWDA4GE8U4AogDDAMHAxwLDr0iBAADDgQMlgQDHAcPIwQMAi4EDAQAxQAOCwIAEgYDBxMABgLIeCQHDI3OYBYCE8Zge4sAEwwjjQASAw4GXgQOGwQABiMXAwwEAhS5Ps1ICw4LAAYMMxwEAgsGDgsMJgwWtgQNCizHYA8UDCsGAgYCDkQLChbICMUQyCgWAwrGWBYANgkBnBMExnEGABYNCgBGxEgQAQYEEwzGcSAWEDYAFjAGDgYDHA4EAxABIAfMIDYQBqW0y1ACAAkKARkN1jgGEAEwFg4LxEgmCRgZBBMLpABAFgQLAsRAAAIoDQ4PAwQAChA=',
b'CKcAWWwBtBoEAxUCBiEFHAMFDgIJDQoJDQIGCggBCRIFHAIRGhEAAgEYCRIGARoJCQEADgwFDgQNCgEqBhENEgABGQEKARkHBRIFAgQBCQgNAAgKEg0oCTgGEgwGDgMFBAEKDQkIxQhYCRgKJAIAASUBAI4JOAoJKgkYCwYCBAIJCAoFAQoGAwcBGBEKJxEJCgQBABQNGAoCDgQCJgINAG1zAhkNBgQNAgQDBgIDJQMOBEMHhLUiBwAGFQ4DNR5+YwTJaAQXBgJ3ZQMEB1MEDSgSxGgAEkUGBAcDHCMCBigCBgwjBwYEDBUGBBYcExcLAhkIDQYCByMHAQ4LBA4SDAcjBsYQAgkYDQQHIxwjAA4ELgIcAB0EDQgJBg56gwwjFwMAyzAdylECBxMMMwwTTC4JFigNAgEHixwTLA4UCAkEKQ0CCQY8AwxZkwwCFi0UAisEDwwDPAcjARc7FCsMDgwLHC4UCxQSFg4EHgIMBAseFAsMMwcjDA4CBg6PHgwLHg8ECwwDFxMXQxEOwXkODAILFAMHAwc2zGgHCgkrlRwUAtQoAgs0Ag0CDQo0Dg8CBA4ADQYABhQSDB8MRB4MDwwUAgbTKBYNBBsODw4MDhQPDg==',
b'CKcAWWwBsAwPAgQKDQkNBh0JCAkCCh0IDQQJGAkKCQwCBAYaFBIUBgkCDTgSKAEJDAQGDQkCBAkIDRuJBCgJEgoYAAgUBgoJEigSCgIAAgYICQQSBggKAAkEAgYJCBJYAq/DeQQIAA0JBAYAGQQGkyIJGA0ECh0JArkIEkgdBAINAscIAgYNBgkGACkNBAAonwQYAjgGmQoBGSgNFBIECggGjDjJIAIKCggpKA0LBA1ICwIYCQ0LEg0KGMtYGBQJWAQLDQgdEgQGCijEOApyaAQSFAESDQkKWBIoGRjLUDgNBg0IDVgEAjg0DUgdCggCCTgJxDDPcFgNCg0IAArEKAoLCn/YpAgODQYAChkECX2IOQjKAQvLeBIKBAl1eB0GBwEJEgsECwTFSAgNxAgNAhQOLxcADQIPlMdQCh0CCwQCDAMXDxcPJgwPDB4kGxQODA8GBAYnkQwEBA4MFx8AkQwPEQQOBgMGAycPDgssBz8MkxcCDgwEAwIGFwMcCxx9vxIOxkEGDB4bCw4cd38XDAQLDhtOG4UMcp8cKw4MLw4EDg8eBC8+uR8CCxx/bw==',
b'CKYAWmwBtAoQCgAGABYqCQgZGgQCDCsOCwQgAQoBGhloCQoCVAJCNg0ZCgk4GQIECxQMBgoBCiANBq82AiYdBgIMABcqLQoJChkKESAcBgMGDCIOAAEaAAoADQotKQoRGkAGAEkKHQYdCQodAAodFkIKFAYNAAkICQ0KBgItChnHCCADBi4UEgYCNi0SLQogBAwWIAYCDhRCDQYSDQoZBgQOFgAme2AGDRIEjggJBA4PBgwQBiABcHAGEgskDh8WABYABkAKFiKGBAsvYfAmEAYLDC8AKgkaAQABEAEgBhAGCgYEPxoZCgEACgHMMAoQERAWBC8MGRh3aQFgAQAMBD9pyCgJCiARIAaWFALAYSnOIL8wAQQMLx8MAhkKKRgKCSoZGgkGDg8cAx8MBhgZCCkBWRAGBAwPAg8DHw4NzQBZCAkYCcYADA4MDgOUBAkNCw4AKAk4yFkMBAwBBw8DDwwSDA4GCAlYGQAJAAYCCwYBMxscBLgZDSodFg4EBgwHugQLDwwEBhIEDhQLFBsEKwAOAwc8HwQMDgsUOw5/Ww==',
b'MHEAcGwBtgsCBAcDBAwDDw4EAgvACwQCBwMMDgN+DwzDDLfGwcagw08LCwx9Dw4OxpGADgMGwrALBM3B0C7NQ8yDxCDGS4XAEgTTwATF7MAcxmDMY8bxBA4EDg7N9gLNbsHlwyzIwAwCDgTJ4LLUwsthgQ7DIYEMzOUO0mLZxYECDMoBxWHEoMXhxiOdx4LDI64CAgaGAgSCjbDBgeLHygPUZtBCx8HIwAaADIfAApfBA8GCAAYAzkOvxYHFZrIAxUcAAMODyaIDxwGVsQAGBwGKjgAHAAOhwAYKAAG3CgGAjgGCwILDwwcKCQoKCqIJCgHEgKfDggrCIQkKCYE=',
b'CJAAbAFwtAoADgIABgACJQYOAAEKEQdRCgEKAgUEBQQBBCUGAgdBGgGQGQAMBQQDBAcGDhUEABEJChEZAQoIGgkNDBUDBBEGBA4CAQkISQodIgQABBUDAgEaAQIBGR1CDTYMAQQDAA4NCj0iDQYdAgQOBAsUHgcMKx4CDC4CXhwCDCMEHA4CDD5MEw4ULgQ1AwweHAMMAyweqQNwhXMHARcGDgsOAgOFMwcTFwABAwYELAMBDgZVBwMnARcxA0wDBg4EAgYHBQEnQQoBABYcbjsEBhIGAgYSXA4MgVweN2EHEyxygwwKAxAGEwcwLBYsDgLACiQ7JB4cDhwGDAMXAwcBAAdME4lDBwMHABYABgwWLAYcLgIGDFYyBCIEwSEGAhQrFCsEKwQeAiwGAgsSBBwECw6MDAMMYwwDDgQMBgQMUwx2gwwzAQACBKMHI7MzDgoEDlMHMwcBjMYoIQMEDgdDBwEjEY8TUQAChnqDB2MBBiDWGFM8AyxDy0gS',
b'CJAAbAFwtAsjBwOMIwYMDhQiBA4EBnxzDBMsjAQOGxQODwsMBhMHIwweZA4CDA4LAgYPCwQADAcDBwMcDgQcEwwCDAIEIgsCHgsMAwcGAgQMDgwONCMnFg4EBA4LDgMAGyQLEiQDFxYAmwsLHgsDBgQGDAMeFwYMsBEAFgwSC8UoHAQABw0CCwYBAgAEDAdRBwLBIQ4MBAcKDhsECgYDBAwGA1EGCw+0HhDIMAQGAwwEHhMHEQcBA8l4BAMOBAcABh4LAJbICBMxAwscqgwDxygOIwQMAhzKeCcPwQkOBAAGBMphAy4MYx8EM48EDDMEHgxjDwwOEwATDgQLAwcTDAQOHFMHDwQMQwADDgPROAtDxBEeFBImU4gTDDMACwSXSwIeDBYAIwcTBxMGDAQCx3gDHB4kCxQyDiIEyjgUGw7HCAIMFhMMEi4EDhIEDgzMIMYQDgIkAgwDANQxBg4CkAweHywbBAIG1gikIxwGAqofHgQMDw4LBA4CFBIGQwylBD8cDtAoDgAEHgYCAJIeb8B5AgQQFgAHAcoA0yh/f5EbB0I2uB8HbwzTISvFSA0rDg==',
b'CJAAbAFwtAsCbwc/Cw4MDgQbFAIUDgsUTxcGFI0PAyQCGwQLAgcDiwwfBgIUHx4fDhQCBhQLBBAHDgQMNA4fDAsAEw8MAgQCBBsEDgIGLgIkDg8MBAwKBxMOBAsEAisHAwwLDwxPoAkRBgcDHAuWDAACCz4fBwIEBhgNAhYHAMZQHsYQHgwHHwYUJhIKrA0ABgwGDADEWC8MBBtUGgYOBCINBg0/jBYAGQoGDTkGDjQCH7kGAAZSrzkKAA0GAgbHWDLKAA0JKg0aDRkKGQoBDAQrREIGAh0GFAINKQwEDQkwBwYNBjIEvhQSAgQKMQoABxAnAQAaAQ0SFBIMBBARAAcAAwAXAScDERcACgEdxhAgAZMXcLEXAQIMDg0AATBRChEKUQfRGMUYCgEAAQoJGgkBg8Z5BwwODxQSDQmTOQoBKgkIEQLVSAYMEhkaSQGhOA0LBgMGBCYAAX16GQrLKAQWBwYMAsYRCikICQAGRAsEHgZQJgAJKAkCBAwTFwMOKwQSFiIOBAIdCRRjDHaLBB4kAgQLDgYj1gh5qxRrJAMGGw==',
b'MHEAfGwBtgvABgTAQZEODAILDAbDR8PDwMIEAsFBwePADwQEt8P2xlHGgw6CwAwOBAQODg7JyASkzQa0waHIAMRCos8WzCHTQsyryKDIwMcBiNEB4CHBYcuBAoKb3E7EALKBw0uwyoOT1wPJIsAClQwCDMFhDAy/wSHEBwwMBgIMDALH4dOEwUHbwgQExQACAs7hwIHTYAaBygDGAAIE1aHFgIoCnwKEgAYG2+HPo8lD2EcEx+LABAwGz6AMDNGjAgAGBgAAAQDAYsGBBgAHAwCCBgABB6wBoAAAkoEBwAIDxOIGAcSABgYKCseBqpDDYchBxgEMBsiBA8jAB7vAQa7EoQfNoMugrAC3AQoJCgnH4AnAAboKgKwJxmHCo8Qgk4a7CQjEAAk=',
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