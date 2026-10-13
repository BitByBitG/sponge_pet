"""Movement and six-frame eating animation, independent of Windows/Tk."""
import math
import random


def clamp(value,lo,hi):
    return max(lo,min(value,hi))


def advance(x,y,tx,ty,speed,dt):
    dx,dy=tx-x,ty-y
    distance=math.hypot(dx,dy)
    if distance<=2:return x,y,False
    step=min(distance,speed*dt)
    return x+dx/distance*step,y+dy/distance*step,step>0.01


class Behavior:
    def __init__(self,now,rng=None):
        self.rng=rng or random.Random()
        self.follow=False
        self.paused=False
        self.action=None
        self.action_started=now
        self.action_until=now
        self.next_target=0
        self.direction=1
        self.phase=0
        self.x=self.y=self.tx=self.ty=0.0
        self.walk_speed=65
        self.follow_speed=220
        self.animation_fps=5
        self.eat_fps=3
        self.eat_sequence=(0,1,2,3,4,5,1,2,3,4,5)

    def interact(self,now):
        pass

    def rest(self,now):
        self.next_target=0

    def toggle_follow(self,now):
        self.follow=not self.follow
        self.next_target=0

    def feed(self,now):
        self.action='eat'
        self.action_started=now
        self.action_until=now+len(self.eat_sequence)/self.eat_fps
        return True

    def update(self,now,dt,bounds,size,pointer,dragging=False):
        l,t,r,b=bounds;w,h=size
        max_x,max_y=max(l,r-w),max(t,b-h)
        moving=False
        if self.action and now>=self.action_until:
            self.action=None
        if not dragging and not self.paused and not self.action:
            if self.follow:
                mx,my=pointer
                self.tx=clamp(mx-w/2,l,max_x)
                self.ty=clamp(my-h-22,t,max_y)
                speed=self.follow_speed
            else:
                if now>=self.next_target:
                    self.tx=self.rng.uniform(l,max_x)
                    self.ty=clamp(b-h-20,t,max_y)
                    self.next_target=now+self.rng.uniform(4,9)
                speed=self.walk_speed
            if abs(self.tx-self.x)>1:
                self.direction=1 if self.tx>self.x else -1
            self.x,self.y,moving=advance(self.x,self.y,self.tx,self.ty,speed,dt)
        self.x=clamp(self.x,l,max_x);self.y=clamp(self.y,t,max_y)
        if moving:self.phase+=dt*self.animation_fps
        return moving

    def frame(self,now,moving):
        if self.action=='eat':
            index=min(len(self.eat_sequence)-1,max(0,int((now-self.action_started)*self.eat_fps)))
            return 'eat',self.eat_sequence[index]
        if moving:return ('right' if self.direction>0 else 'left'),int(self.phase)%4
        return 'front',0
