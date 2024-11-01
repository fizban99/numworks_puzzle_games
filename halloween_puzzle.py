from kandinsky import fill_rect as fr, draw_string as ds
from numpy import  zeros as zs
from time import sleep as slp
from ion import *
import random

const = lambda x: x
_ID = const("int")

FG = (0,0,0)
BG = (255,255,255)
_BLNK = const(0)

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
    cur((255, 255, 255), pos)
    pos[0]=(pos[0]+vx)%4
    pos[1]=(pos[1]+vy)%4
    cur((0, 0, 255), pos)
    
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



palette = b'H/fe7zzWeL22lFCs83uOYopBhzFGcwxJ6CkFUikgxLQPm22iqorLemnCqsON5A+zTMxw3XPay9tt5LHuUu4O7Us='

data = (
b'CJAAbAFwsOABgBHwAAEAERIz4BECIyQFFHqgARABBAWBNgcICXCAERMFBhgGCgYHCwg8cAEGCIkpCw0ICQwOHAkMUAECBykIPAkMLiwICTABAgYJHA4cDgwOCTwpGAsAAQMUC0w+LA4cGAsdBwQKDQg8f36eCQs3CSx9vjwIkw0LHE4Me34cGQ0LgRscHgwODHt+LBgNCI0YTgxwnhwZCCsICwjuCQwJHAkYCwgJCHDuHC4MGRwIDCweDG48Lgk8CAwJHhx9jhw+xTCdDMkof46hyUkIDA0IDHa+DE5cGD4cfgxexUgJCwkePF4McK4MCwgMOQ4czhweBwsZCAwOPHC+DB4MCQgbDB4JDgkcniwOCQgNzQDDCQx4viwICwwOLA7FSA6fbikM',
b'LFAAdWwBsgMDAwUEBAUCiIAGBAoHCowGCgoHBgUEBgoHBwoGBwoNDQgLCw0IprINCgoKDQsLCAkJCYcMwAEKsAugCA2YCQwODg6rwEELDMJDiA4MCbKqwYHCAp2hDgkJwULCsYebwREIDAkIw5GLDsWiDg4IxEIOBwvIcMJxxHLACAwHBw0Nt8GiwecMDg2yy+HEQcdAwXWGzmDNYcVCwzbIg8MgwXHKY8GkyPG0DQjQc84ywzQL0KEIyFHDUZfMAbXLUMRQCwusCcGS0hHE0QnEoAsMDst0uwjP8MNCyVALwtHS48OTx0IO10CywUHSUdmDjMMg22EJua+bxEEIyuDCAMtRnsJRwoEIwYHdoMDBnwbQkt5TDQ0H00DCowgJDQfHwsZhC84Qsg0HxfHGgA0KxQGXCbTYUAsHznAI33AMCgfQIMHCxpANB8NAyIANzqHEIMoEDcgwxRCyoN8B1GHIYcMR3UEH5mHNMM7QBwfOMshAwZHEIM5w0aGiCg==',
b'CMYAOmwBsAQC8IAGAyABAgPwIAYDMRUCAfAABwQDBQMFBAoGAwHwDAkLGhcNBgUCAeAJHCkICwYFMcAcDhwJDAgHBQMCMQABgDwODAkIChYFIgMBe5AJCCkIjQsNBgQGBAUDEnhwCAkICRgJDLgHDQoGBQQDAWdQCDkYCSwZCAsXBhQDAkAJHAkoDBk8CQcaoAQDAiB/PJEMDhkMCAkoKwcEFQMBHAkLCBmyxVgMCBvEKAQFyEgNBw0IG8VBCSvEUArIeMggxyAWBw0LDAkMGRi0Bw0MCAsIFrElBgcLCX48OaQJBwsXFho0BgobHA4MGQweDAoLBwYNCiYkBRQHGwwZHC4MCg0GJ44EBQQGGKEOLA03CgcaBhQPBBXGMAlzTBkHCg0HJgomNAsILMpIDA4cCgcKBwZ5RA8UBhscGMxQBgcNKgYEDyUEGwjHeTkcCQYXoBTSeAXJaijRECwKDRoGChQPAwUHHRnOWB0JDB7QCBbHQAoHC8M5DA0IDQcd1HA=',
b'MBAAbAF9sPCgwDQDAhFw8GAEIxHwQA0KFAUSAfAgCAsNCgStEAwICZapACwJCA0GEwEAgnDADjwIDQcKBDHADA4sDggbrgUDAXCgDC4JHAkYDQoVEwGQLB48xeDIoLBwgAwODB4MKQwJCwcKFBUCAWAJXAkLCAnMoAcKJAMBUEkMCRwIOQsqBAUCETAMCQwZbAkoBxoGBQMCASA=',
b'LGYAeWwBsg4ODAyFDggJCQ6SDsAIngkMCYC4CcGmkwynCIfCEMNYwyEICwuyCIAJxZHBg8RxC7MIvgsICwnDN8KwCw0Luo8NDQvE+MRirMMyyEm1C8Mww5EIxcDMhsUBDAnE4MfyyBLGAcOiwnCnhMmizZEHC5zLUtASxALBoZ/DQMIxkgvFp8hwzZIMzjMIC8xWn8dxwzHK8Myw0rHCkNQyCAzEgs7BCw0HBMTTwcPC8Q3OEM/ABxARwaPPwbINBwfEwQgIBxIRwaHIQQzC8gcHDQoNDcUAChMRE9F1x4EH1GAKw2DR0LIU3YMMDJ/GEAcK0zANshERtNSh2bUKgAkLB7MVFcniCA3M4cNgBgoGCAjDMRMUFRbPsgcHzKMHBgQKCA0LExQTFxUYFaXLIg0HCgYEA8agBxMUERMXDxgXCwfF4AYKCrEFAwMHB8aAw0APEhgSCgoEBgQEBAYGwZEEDQoGy3ARFBESEhHEQKSABbUGDQoTExMRFRQXEhcWBQMCgRkCwaENB7ATFBQVEhAPGQ==',
b'CGMAfGwBsgyACQkNDQ0HDQgJCAgICQwMDsCRCA0Kh5ELDYELoAsIwNILrQoJwMoICwsIDQcHBw2TwVkLCI6JwLmyBwoNDQoKCwfAYQsJCwsKCcMIigcKB5oKBgrCkMLAwPEHw8AIxBiZgAqAB8SRCg0GDQoICbvDMsDBEgYKCgbCuAYEAwe1w4iqmBERFxcRFRYPEBAQoQcNCQvCCMLoExcVGhsVGxsaFRASEhAPGA+VCsJwwMIaGxsWgxUXE6wQGMgZBwYEERQaFRsWshsUFBcTExMREMMYsBIXFxQaGhaXwAEYFcOAFxUTDwYKExIRFBQUwygaGhUaFBUQEBIREREVGBcVDwoTEREUFRXDIRoVlBISEg/CKBUVFxkGERPBoRsUw3EVFxLFwJ0SEhUVGAS0GhoUGxoUEZgPGBDHERMTFxgYEBDDSRrDYRMTDxkPxLgTDcURFQ8QwnEUFRHHOBcSGAoHBgYTEhIXFRcVGBITEMDLEhPC2AcSEBKaD8OYFBATEArAycVxHBkQDxIXGBLFwMAhExMYEMfoxwjJGBgWGBcPE70YEML4DRIVEstYFMg5FhwWFhgTExQbFhcXGMMAFw+7mcrJFhsWEsjIGxbIAA/HwBASGMGkmhUTEsZAvRYWFxLFmBbJ6MDLGxMTEsfQwFEWFhIYEBMczQjAyRYbF7QazajA0cbIFxLAqhYbwjDDSBbA0hzEUBUXEBE=',
b'CGMAX2wBsgcHBgQGBgQFBQYKDQkMCQkMCAsLDQcNDQcMDgcKBpmACgeaDAwJCA0NDQgKBwsJDAcHCgqYtAsMDg4OCQnBqgoNCwsJDbUED7QKCAwIwoAICQgIC54LCwihw1EGCgeTlwuDCcOQggvDiAcQBAfDyMIADQgIw3jDiIIJk8NhwNEGwdmoDcKAtgyYCsUIB8UIB5iZgMIIDQnEMMNgxCAFw5oEBg0QFxEQFxAGu8QxCgQKEBUXDxO1ExMTEhEQEREXGA8QxrDHmAoSFRUXEMC6ERIXFxIXEZ3A0gSaFhUXFxESEhIRFRYWGMDRFMKBx4EYFhgYEBMSE8DJFhsbGxQUGspQwooYFhwPmhUWGxwbGhqCGhoKx0gQBQUKDxcVw3ISERQVwLmAxnjHiAYHGBcSExcYGA/EUBERwNMQGMUgBgUQFxYYxBAQGA8KxSkRFMKgChASDwQSDxkPwyjFgBAXGJsSFMDZE8LwDwcKGRgXwxAUERURxqgVEMKgFBoStQ8KChAZHBcVxLgUnhcVFhfBuRASBwYP0OgYmxbFmhQXFhwWFxUYEBcTBxIQ0AgHGBwYx2mbhhwbFQ8ZFxMNExAQBRAKDxkcDxzA0sTgGxsWDxLA0RcPDxIEExkZGQ/AyxrJWRYQEBISEw8QD7eawpDDcpgbyxgSERLDiA8QBBgcHBzKSMJgwnCAHMYQEg8QEBgSGBeOFRvE6MQpwOE=',
b'KGQAcGwBtgkMDgwMDAkICwcQFBrAARsWERcXCg8PGK4MDg4JCQgIEhO3GxsbeBwYFxUTExccs70JCAfA2RsaG3gcHBURFRISFcCxwCELBA8TwoMWFnscERUXE6nDeA7BsQUQERTBqMDZFxcXDgjBtwoEEhcRFLe7FMFoCcGzDAgNBhASFRQVrxa+oMTxxhkItxcbGxWwt8NJwcrCmQgNChAVFMXwsMGowmIIC8G6x8oVrYMMC8F5w3DEcLbEWQ/DUhoaxOuKwqDBEQsHBwoPw2gWGxrDNcbyxhINDQcGGBi2xOrBvMmiwVgLuA8YFZLBusERjMp6wdIKBAsICAsLv8FgwfsJzSq4C7LAEYLC28VowDHAksEIgA3CmcASwOEHwKHAKQsNwsi1CMHJDAwKB8GRBwfCaMKwwJHA0YQEBrjBsLS4w2MNyMjB2AW2CgrBwMJQuwnFeQ3EWgUEgLq4w0HFOsAiCAECubcNwbHEYKjGkMKQALYFwqkHBwfHAcYygQkJALYDwboHxHnA08WoDQsAtgHBusVSxvPAGg==',
b'KGAAeWwBthkeHR2EHR6AH8AZGAoQAgUEBAUFGKy5qIEeEBIKDwIdAwQCAgIZHQLA4R0fHxWCwbiWAQHBuAbAusGxsB8SHw+2AgEBAQUGBMGpwUHBsREXuR4ZBgEAAgYEBRnBtLWBtAYFAQDEOAYdAsNZwwnA1A8PAgACBLYCxDTDYcDRDxkBAQABsgPFILbGqcaQtBkHBwYGBAYGBwYFBRkFDxkZHR4Zx4LCuBnHYAQNCwsNBwUFAwMDGRkYHhjAAQMFgAQGCreSGcDhpcSwwljJIQUECg0Fw2gDBQYKBw0HgIgNBw0NwFkGwemOCgcKEhPABAqABwq+kZ4RgBQXFRUUkRERFxMTB8E6ERQVFIQVFRUYhsBBFBTAzBUXF8GQFcU7gRUPExMLExcXwmq6D4IQDwQFD8E5wyEVERfDKBcXEBIQEA8QihIQshcRFIARERITEhLBcBLFqcPxmA+xksGgwVgGoBgPw0APEBIRErHBGBC9Fw8YyKAYD4DHIRDH4LnDuRfJSMkoGYAYFbiyERUcHBYbFRIKxCITBwQZGZ4WExEYHBYWHBwZDwrP2MABGBIKtBbBeMEQiAXAytRRHh4QBhwcGxsZFhwZurIVrs9iz2gSDxYVGw==',
b'KGAAcGwBthwWHBwcGRkKChgeHx6FiB8fFRMYFhbA0g8HBqmvwNEfEw8WtsGYGQoHGcDLH8HbEBLBsbcHCh0dHcG8gB0eEBAbwasCCrXA64gZHQYQwZm2A8GqBQQKChIPwQkEGQoXGhvA0RkHBh0dEA0TERQXEgoZAh0QBRMUGsKKHMUAHRgHF8TRHxcKGRgEGBEatRUXFw8HBB0PEsDJHx8QBQ8EFRobExAPEBMSEhIKBh3HmMaTDwQQERQaFRIQE8MAFRXDCBAYHsUIxrAPDxPCcBQTDw8YFxEXGxcKBRkZxeEcHh4SEsQYGhsRChEXGBXImBIKAwK1yfETFxuBE8opkREHBgUFDw8PEhMTmsT5ERobGxYagBsVF8JIExERFBsWwMkWFau1gRTDGRsWHIsbG8YAwLPAMsFowZnBAMBClMC6ocDBiBwZwsmkhcGUwR0WwKmKwDK6wZDDcBzEMMDhwMPCQrMYzGgYEsChxfLESBQVFBUXFRcQEcqxxkDGUMWwjxERxsgSEBAXFRYYEtKYFRXA6cABthIHzEgYGBAHGB/BEBW8F8GAwZATEwrBoBEXFxMQzcAQEZLDGcForJYWwnAQzeARw7AVwagXEMEiFRXEqRAK0rAf',
b'KGAAbGwBshITEREXFxAPEBgcHBwWHBcWjBwcGxsWFhwTEBEUFxgPGQ8cHBnAqhYcGYEcFhLBoBUYFcGAtMFQGBATCgoGBgQEDxgXFbLCUcJ5GxgQr4AKgBEVFBvBgBaBGxewEAMCGR0eHhgPChcVFbXCWBYWFxMHBwcGBbAeHh8eHRcbxGjCYRYbDwcNBxMSEAoQtYAUwXHE0hYSDRMXGx8fGBASrsHQF8QVFhoTExoftB8eD8G4HR0eFcGKw1EaExfAyh4dEom1wanH6Bu0gR0eHQrBAB0dwNHF2xIRHx63HhkTix0Vw0vJqRAPwMkfHw8TxdgeHco5w0nGGBASHcDSEhCQtcdqthYVExnKcRATEMeiHcvxx5nBuRMFBQ8YDw/HjLTIc7UQEAHE8IDHgR4dGhoWGslTHBvCiKbA2YsaGhsahsbaGxISGafBoR0YDxYbwaDBtclYEg/BqRwPEhHK6MDKz5CUGhXRMB0ZDxcUwlATEcXpzYjQaYQcHQIGD8MZGhQKExLF685wuxwFBwcXsxoaHQ8KEtCg0aqPDwoNEMJyGhseHtAgyirNkRsSCgQTFREUFMTYGso4DxPMzRcTEhwSEhoRwai0yJEQBhjESdQQDxwVExQUEcc4xcA=',
b'KGAAcmwBthwWFhAKBR0eHh4dgIgcExQaG4AaGhwcFhkGCgICq4EZFxIbFhYWtxyADwq3gAICGRUTD8JAwaEbDxkcGRkQEwcGBQMBAQIYFxMRHMGRhxMPGBkZGRwYFxK8EBMTF7IVFRcVFxAQF4YPBbgcFpwPwlrDYBwcGBWUFhUQEwQPDxUcwtAcGxsVGxUYGBgZGA/BIBQVFhYYFQ+eFcKwEhESgRcSEcRQGriAGBcREhERDw8XDw8QEBCUHMDZGxQXgBQXFBEUEREXERQVw4DDSMU5xXLHSJnAg8F4lscYnqvGehYWrYXFW8dCwWIakxXDwMVYwkm0wYOKx4APEMdxFRcXxjkcwlwYDxUYxRAGCgoHBwYGD4AFusEBGBjFyAoHDQuCDQcHDbzIaMIIxngGBgoNCwsIDQcEBAkICAgLwQiHi5wIDQoGBAUECgwMCQkMwPmyBwqpBQMCAwQFAwOxDAi7CwfAsQMCgM+ZAgmBwbHBkAYFwYnPeNFItgjC6AvBkML4s7QZwMGGwyLEGMGYwaIZ0eLS+sT5xhGytAPBkMC5wcHBqbgHBsTYAwMFwLMfgB4Lwai6wajFeRjA0sDJHsNACAnHIcJyH8MZHh+3GB4=',
b'CGMAdmwBtgUFAgECAgHAAgAAAMAZAIoEBAAABQYEBcDDocETmgADowYEBAYKAwICAwMDBQQFAwKKoQMCvAQEkQXAqYXC6KS7BQOaBanBkcG1icLIwNEBwZHAAZPABcKBBAIECsFBmMAJwdHCAgLEMMTgwMHBq8P5waLGPcUBDQ0HDQfB+sECAZywlg0LgwgJCQgLCw0KBsGjBcFBCwsICJcJDMABCQsLBwbDSAAEwokNm5nA2Q6aBwoHlgHA0gYKCge4CQkOwAIMDQoHlgMGBQEAxBAHC8GRwMIODggHDckgxsAKAhMTxDibwLqDmgTFqAQGBwMUERISEsOCw1DDiAgIDQ3IMgIAEA8QEhMTEg8QEwsJCw3A4QvDYcABFRgYGBwYFxAKCgoNCAsNCMUoDQXA0xcVFYKfFxMHCAnH8AsLCgfA0w8QEBIRnJ0QxikHyNDCjBASEMNQExCdHA/JsAbKkArBqxMSEhDFGIYSFxgPE8XQyjDA1MGZEw0TExcXEhIEGA8HB9GJxQsVFREREhAQEwcSFxETEAUFB8T8mhcXGMUgmwq/EBAHBwrBrRwWGxcRxRAYFcOQExMKBQrBthsWFhoaFBEREcbQEBIKE89oBsQ0',
b'COEATWwBshsWFhYPFxYcGQYYGBATExccGRgSExYfHh4eHxsbFhsVDxwcGQQQGRwVEhMQDxITF8FJHmsfFhoaGhcYFhsWGQoZHR4fBgoHExXBSh4eG5oRFZocEA8dHR4dDw/BRB0dxQEXERQaGxYVEhgefR8eHcFDHg8QBJMbGxIRFYcEEH8fsbmeD8cgGhYcthIRxTgYwzLEUR0PExcWxlDLaBcTxRAaGg8SGcYzBBIVGxsawREbFRMThxsVChjGUhASF5kaFBsagRcSwVsSmxgSEsJ5lMs4GxoVyiGNEBAZBcc6GxQbGxfFKBwbFBEXE8EBFhUVExcaG4CaDxHUKRsRFRHFUMw4wAQWxGgYFxsVHBytERPBR9U5xQAQoBgcFhcQExUVxRCWx2kWFRYWzygXFRcQHNkKxgDLKNAhFhgWFgcSEhixGxvaMBIRFBSdx1gWFhgVHA0TEw8SFRMRxVDBWRERFRcVxGjICQraABC2GBafERISD8kAHBIcEhsQGAYGBAoQENpgGRwQEhUQxBDWKBMYExYQEgQKBgYGqw/IOA0TCsdQDxIPEAWuBwABAgIFBgoKEsARm8ADBsERAMABnoAZwCoDBQQFAsEawVLAgF0=',
b'DOAAYmwBsh4fHh4eEAoPHBYXEhIfHR0PExoUERsaHBYaGpgdHh4PChASEhgeHR0dEhEUGhQbFhbDIo8eHQ8QGIcdHQUTFRoUF8MSxlHDQ8ABHh4SFxoUFBXDIxAfH8JjwyLNEM0hGxYbmhMSHMJ1HR4fChjNEBQWwyMUEhPMU8lQHxIQwykaGxcTEMMSHx+lFIAVwxIbGhsWHBgSEBkBzHASEhMUERQbF8ZDzgDAARASDwIPBxjaMBEVFRUcHBYbs6CG4RATBxIVExQUExYXGMMRFrjDEYkVERMXFBQaERHJcBwWFrgUFJrDcsdRGxoSFxYPsBYWFRYX3wCRzkGFFRcTkrIcFRcbERXUQdVQxBERFw8SFtBQGBUXmhIYFrARGxSSDxcQEhUWEBYcEtRwEhXLMBrPQJwRGBIPEhOvFspQig/jEBWaFBEXEd4RFxXrIBcQGBIYGQUKBhURERQSFxEQzHASFw8QFxobEA/3QAQGBwYYEhIbEs8gHA8PEgcHCgcSBgoKCgcHBgUBARcQEMwAHBgFBAoKBAUFBAYGBgQEAwIBgMRBCoQGBQIAwAHCMQHDEgAFAwOCAgHCcsCAaA==',
b'DGEAeWwBthobGxbAERYbFBQXEhISEA0EAQEAwAIbFhwcFsABFxERFRUXEAYNA8GUABYcshgVFRUREhITEhMKBwYCwaWzERexgBcXFwoKDQXBphAQEBKDwGK2EAfBlgCqF8fgtBISBw8ZBATBqMYgB8ZAEhIKCgYEBQrBlwDGUrESERAQEwQKBQLBlgARFBQUGhQXDwYTEw8ZBcToAAAagM6wExMKEhgCBs02waMUxOHJ8AQFBQQAwakbERMTExAPBQTIMAcEAgbBuBAXtBAKDQoEBgcKBAQGw1gGChASB5gHCAjB4QXBqAsHBw0NBw0ICQgICAsHBgPBqAcNCwsJwALBoQrIaQYLCQwMDJmECNdgwagKB8GhwbG3BgTBqQIEDcNiDMaxAwXeFcGiAgUNlQwIC8hAAQPDWgIZBAfLkAkLDQoFALbBpx0dHQMGymENBwcCmgQEy/YdHh0ZDxAKCgfa4AEBBgYDAsG2mgMCqwQDCgIAAgbFAATbNR0e30DVoAUG1ZECAYADzCQdHQ8ZHhkZA+SAAQECAgK/4fDBoh4ZDxgdHcGBAgPAAojKVA==',
)

z = 2
img = TI(fb64(palette), z)

key_pressing={KEY_OK:0,KEY_PLUS:0,KEY_MINUS:0,KEY_ZERO:0,KEY_ONE:0,KEY_TWO:0,KEY_THREE:0,KEY_FOUR:0,KEY_FIVE:0,KEY_SIX:0}
key_pressed={k:0 for k in key_pressing}

tiles = [t for t in range(16)] 

draw_tiles(False)

ds("[+] mix",226,160,FG,BG)
pos = [_BLNK//4, _BLNK%4]
cur((0, 0, 255), pos)
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
    if keydown(KEY_LEFT): move(-1,0)
    elif keydown(KEY_UP): move(0,-1)
    elif keydown(KEY_RIGHT): move(1,0)
    elif keydown(KEY_DOWN): move(0,1)
    if key_pressed[KEY_OK] and not solved:
        for vx, vy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            new_x, new_y = pos[0] + vx, pos[1] + vy
            if 0 <= new_x < 4 and 0 <= new_y < 4:
                new_index = new_y * 4 + new_x
                pos_index = pos[1] * 4 + pos[0]
                if tiles[new_index] == _BLNK:
                    clear_tile(pos[0], pos[1])
                    tile = tiles[pos_index] 
                    img.s_img(data[tile])
                    img.dr_img(new_x * 27 * z + 3, new_y * 27 * z + 3)
                    cur((255, 255, 255), (new_x, new_y))
                    cur((0, 0, 255), pos)
                    tiles[pos_index], tiles[new_index] = _BLNK, tiles[pos_index]
                    matches = show_matches(tiles)
                    if matches == 16:
                        ds("SOLVED!!!",226,10,(0,0,0),(0,255,0))
                        solved = True                    
                    break
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
    slp(.2)