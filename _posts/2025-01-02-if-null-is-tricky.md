---
title: MySQL IFNULL is tricky 
layout: post
category: software
---

I started the new year with a very puzzling bug. One of the users of my internal dashboard tool told me that he doesn't see some of the rows he expected to see. I checked the query that populated the view, which had various filters but none of them looked suspicious, expect one of them. There was an `IFNULL` looking at me in the query which smelled awful.

```
SELECT
 ...
WHERE
 ...
and IFNULL(CUTOFF_DATE, '0') <= '${BEFOREDATE}'
```

For context, the CUTOFF_DATE is a datetime column, and the 'time' part of the datetime is always 00:00:00. So a typical value is 2025-03-31 00:00:00.

At a first glance I really didn't understand what was wrong. Then I checked my understanding of IFNULL by running a bunch of date related SELECTs:

```
SELECT 
    CAST('2025-03-31 00:00:00' AS DATETIME) <= '2025-03-31' 
UNION ALL 
SELECT 
    IFNULL(CAST('2025-03-31 00:00:00' AS DATETIME), '0') <= '2025-03-31' 
```

The first one returns 1, the second one returns 0. The value is not even null, so I didn't expect IFNULL to change anything here.
However, looking at the MYSQL documention explains what's going on very clearly:

`The default return type of IFNULL(expr1,expr2) is the more “general” of the two expressions, in the order STRING, REAL, or INTEGER.`
https://dev.mysql.com/doc/refman/8.4/en/flow-control-functions.html

The IFNULL statement has '0' which is a string, which makes the return type of IFNULL string, even when the value is not NULL.
This practically changes the filter to the following:

```
SELECT
    '2025-03-31 00:00:00' <= '2025-03-31'
```

And this returns 0. (because they are strings).

The solution to this puzzling problem is to simply make to both variables in IFNULL is the same type, so you are not tricked by the generalization of variables.

```
SELECT 
    IFNULL(CAST('2025-03-31 00:00:00' AS DATETIME), CAST('0' AS DATETIME)) <= '2025-03-31' 
```

Returns 1 as expected.




