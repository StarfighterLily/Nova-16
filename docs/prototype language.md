Arithmancy language: combining necromancy with arithmetic.
Programs are written as spells, wherein the caster raises zombies to perform basic finger-based arithmetic.

Zombies have two hands, with 5 fingers each. Each finger can be up or down.
Zombies can add and subtract on their fingers and add them to memory.
Zombies have memory, and can remember up to 8 things.

```arithmancy
raise z
z,r:11000
z,l:11100
z,think r+l
z,speak // zombie should output 5
z,r:think 0 // zombie's right hand should be 11111
return z //destroy zombie
```

raise z1
z,r:2