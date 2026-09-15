# Research: what look-back numbers users of food trackers actually use

Date: 2026-09-15

## Question

The vault stores one closed Day node per day. Each node has the seven eaten totals (calories, protein, fat, carbs, fiber, sugar, salt) and a verdict against the one fixed Goals target. A weekly or monthly look-back is computed in chat from closed Day nodes. Nothing new is stored.

What look-back numbers do real users find useful? What do they complain about?

Each claim is tagged `[user feedback]`, `[research paper]` or `[vendor text]`. Vendor text only describes what a feature is. It never shows whether users like it.

## Summary

- Users judge the week, not the day. Several Cronometer users say they average the days and look at a weekly goal. `[user feedback]`
- The most requested look-back number is the plain average per day over the period. Users compute it by hand or in a spreadsheet when the app does not show it. `[user feedback]`
- Protein is the one macro users check for consistency across the week. Calories are the other. Fat and carbs get less attention. `[user feedback]`
- For weight, users trust a moving average and ignore daily scale values. Day nodes store no weight, so this line is out of scope. `[user feedback]`
- Streaks help until they break. Then they "reinforce the feeling of being a failure." A hospital stay or one missed log ends them. `[user feedback]`
- Red numbers and over-budget colours cause guilt and shame "regardless of how much they went over." Some users then punish themselves. `[research paper]`
- Calorie banking is a wanted feature for some, but the response from other users is: view the week instead. Do not roll calories from day to day. `[user feedback]`
- The main data complaint is wrong averages from empty or half-logged days. Users ask to exclude untracked days. Cronometer added a "Complete Days" filter for this. `[user feedback]` `[vendor text]`
- Other data complaints: no export without a paid tier, and weeks that start on Sunday for European users. `[user feedback]`
- Recommended chat review: closed days count, average per day versus target, days on target with the most common miss, protein days at or above min. No streaks, no red, no banking, no charts.

## 1. Numbers users say they use

### Average per day over the week

- A Cronometer user: "What I try to do now average out the days ... I don't focus on just the day, but rather the weekly goal." He varies macros between days to "keep a variety." `[user feedback]` ([Cronometer forum, How well do you hit the daily targets](https://forums.cronometer.com/discussion/3756/how-well-do-you-hit-the-daily-targets))
- Another user: "I tend to eat above my calorie targets on 2-3 days and then have 1 day where i eat below ... Are there good ways to track these things on a weekly, biweekly or monthly level?" `[user feedback]` ([Cronometer forum, Weekly targets](https://forums.cronometer.com/discussion/comment/18396))
- A user who asked for a daily carry-over got this reply: "What you're describing could be thought of as more of a weekly perspective on your budget, rather than daily." The reply points to the weekly report average. `[user feedback]` ([Cronometer forum, Carry over calorie balance day to day](https://forums.cronometer.com/discussion/comment/21242))
- A user asked for a "week to date calorie deficit" indicator on the daily diary. `[user feedback]` ([Cronometer forum, carry over unused calories](https://forums.cronometer.com/discussion/comment/11672))
- Users who want exact weekly numbers keep an Excel sheet because the app only shows averages. `[user feedback]` ([Cronometer forum, Calorie Banking](https://forums.cronometer.com/discussion/comment/13128))
- MyFitnessPal community threads with titles such as "how to see weekly calorie average", "Weekly averages" and "For those tracking calories by weekly totals - where do you find these numbers?" exist. I could not read their bodies. See Unverified. `[user feedback]`

### Protein consistency

- A user reports she hits targets "somewhere in the 80s" percent and finds it "very tricky meeting certain macronutrients you're short on without inadvertently overdoing it on others." `[user feedback]` ([Cronometer forum, How well do you hit the daily targets](https://forums.cronometer.com/discussion/3756/how-well-do-you-hit-the-daily-targets))
- A user explains that the "Complete Days" filter lets him "see how much protein you've been averaging over the past month" while he skips travel days. Protein is the example he picks. `[user feedback]` ([Cronometer forum, Mark Day Complete](https://forums.cronometer.com/discussion/6933/what-is-the-benefit-purpose-to-mark-day-complete))

### A very short list of numbers

- A personal blog by a user who lost 40 pounds with MyFitnessPal: he cut tracking "down to what really mattered: Calories. Protein. Cardio. Strength. Weight." `[user feedback]` ([Jeremy Lundmark, Substack](https://jeremylundmark.substack.com/p/the-uncredible-way-i-lost-40-pounds))
- A Hacker News user on why manual logging works: "It becomes just slightly more effort to eat something and it makes you stop and think." The value is in the act of logging, not in more numbers. `[user feedback]` ([Hacker News, AI calorie apps thread](https://news.ycombinator.com/item?id=44220135))

### Weight trend (out of scope for Day nodes)

- Hacker News users on the Hacker's Diet method: "You weigh yourself daily, but only pay attention to a moving average." Another: "The 7-day moving average is what I pay attention to." `[user feedback]` ([Hacker News, TrendWeight thread](https://news.ycombinator.com/item?id=39301552))
- Cronometer users asked for rolling-average weight charts and said they use Happy Scale, TrendWeight or a Google sheet with a "5 Day Rolling Avg" column instead. `[user feedback]` ([Cronometer forum, Rolling average weight graphs](https://forums.cronometer.com/discussion/562/rolling-average-weight-graphs-a-la-hacker-039-s-diet-trendweight))
- MacroFactor describes a "Trend Weight" that filters daily noise. `[vendor text]` ([MacroFactor help, Weight Trend](https://help.macrofactorapp.com/en/articles/21-weight-trend))
- Day nodes hold no weight. This vault cannot give a weight line. That is a known gap, not an error.

### Research on adherence

- SMARTER trial (N=502, 12 months): "higher adherence to diet, PA, and weight SM and to calorie and PA goals was associated with greater odds of achieving ≥5% weight loss." Adherence fell over time; the feedback group fell less. `[research paper]` ([Burke et al. 2025, Obesity, DOI 10.1002/oby.24234](https://onlinelibrary.wiley.com/doi/full/10.1002/oby.24234))
- GoalTracker trial (12 weeks, MyFitnessPal): the arm that tracked diet from day one logged a median 5.3 days per week. The arm that started diet logging after 4 weeks logged 1.9 days per week. Logging frequency, not the daily result, drove the outcome. `[research paper]` ([Patel et al. 2019, JMIR mHealth](https://pmc.ncbi.nlm.nih.gov/articles/PMC6416539/))
- Retrospective cohort (7,000+ app users, 5+ months): "Consistent caloric intake on weekend days and Mondays or consuming slightly fewer calories per day on Mondays versus weekend days was associated with more successful weight loss." A flat week beats a saw-tooth week. `[research paper]` ([Hill et al. 2018, JMIR mHealth, DOI 10.2196/mhealth.8320](https://doaj.org/article/7c2ff48fae2c4e5b8305caf95b154415))

## 2. Features users call noise or harmful

### Streaks

- Cronometer user: "yesterday I was in the hospital. Now my streak is broken." Reply: "Features like streak are supposed to be encouraging, and they are.... until they break in the middle... then they reinforce the feeling of being a failure." A third user is proud of a 730-day streak. Staff later added a manual streak reset. `[user feedback]` ([Cronometer forum, Streaks](https://forums.cronometer.com/discussion/5792/streaks))
- A MyFitnessPal user lost a 340-day streak after one missed log and was upset about not reaching a year. Thread title only; body not read. `[user feedback]` ([MyFitnessPal community, Lost my streak](https://community.myfitnesspal.com/en/discussion/10297030/lost-my-streak))
- Qualitative study of 24 women with eating disorder behaviours: apps drove obsessive logging through "reminders to log and gamified aspects (e.g. streaks)." Users "became very anxious when they stopped using it." `[research paper]` ([Eikey 2021, BJPsych Open](https://www.cambridge.org/core/journals/bjpsych-open/article/effects-of-diet-and-fitness-apps-on-eating-disorder-behaviours-qualitative-study/2D1EE739D97AB3EFC6573835E4C527BD))
- The blog user above saw his 365-day streak as a win. Streaks are not bad for everyone. They are bad when they break for a reason the user did not control. `[user feedback]`

### Red numbers and guilt

- Same study: participants felt "guilt, embarrassment and shame over exceeding their calorie budget and being shown red visualisations." Some felt bad "regardless of how much they went over." Green remaining calories became a reward for undereating. `[research paper]` ([Eikey 2021](https://www.cambridge.org/core/journals/bjpsych-open/article/effects-of-diet-and-fitness-apps-on-eating-disorder-behaviours-qualitative-study/2D1EE739D97AB3EFC6573835E4C527BD))
- A Cronometer user asked to see the deficit instead of the remaining budget because it is "psychologically more encouraging." Framing matters more than the number. `[user feedback]` ([Cronometer forum, Calorie Deficit by default](https://forums.cronometer.com/discussion/comment/5539))
- MacroFactor advertises "no warnings, red numbers, or shaming when you go over." This shows the market sees red numbers as a pain point. It does not show user opinion. `[vendor text]` ([App Store listing](https://apps.apple.com/us/app/macrofactor-macro-tracker/id1553503471))

### Calorie banking

- Some users want a bank: "save up some calories on weekdays, so I can splurge a bit on a Fri/Sat." `[user feedback]` ([Cronometer forum](https://forums.cronometer.com/discussion/comment/11672))
- Other users answer: use the weekly average, not a rollover. "The specific 'budget rollover' you're talking about doesn't exist" and the weekly report "provides accurate data while allowing flexibility." `[user feedback]` ([Cronometer forum, 2025](https://forums.cronometer.com/discussion/comment/21242))
- The 2018 cohort study found that people who ate more on weekends than on weekdays lost less. Banking toward the weekend works against the data. `[research paper]` ([Hill et al. 2018](https://doaj.org/article/7c2ff48fae2c4e5b8305caf95b154415))

### Too many charts

- Cronometer users asked for rolling-average charts, then said they use a separate tool and would "rather them focus resources on different macro targets." `[user feedback]` ([Cronometer forum](https://forums.cronometer.com/discussion/562/rolling-average-weight-graphs-a-la-hacker-039-s-diet-trendweight))
- I found no direct user complaint that says "too many charts." See Unverified.

## 3. Pain points with stored and shown trends

### Empty or half-logged days break the average

- "There are some days - particularly when I'm traveling and eating out a lot - that tracking calories for the day is nearly impossible." Blank days average in as zero and pull the graph down. The user asked to mark days "not tracked." `[user feedback]` ([Cronometer forum, 2018](https://forums.cronometer.com/discussion/650/mark-days-as-not-tracked-for-averages))
- "I recently went on vacation and logged no data. My question is how are the days without data treated in charts, reports, targets?" `[user feedback]` ([Cronometer forum, 2023](https://forums.cronometer.com/discussion/5896/days-which-i-log-no-data-getting-used))
- A user of one year had never marked a day complete and asked why he should. Replies: it filters incomplete days out of averages and locks the day against edits. `[user feedback]` ([Cronometer forum](https://forums.cronometer.com/discussion/6933/what-is-the-benefit-purpose-to-mark-day-complete))
- Cronometer's report offers "All Days, Non-Empty Days or Complete Days." A half-logged current day "will bring your averages down." `[vendor text]` ([Cronometer support, Nutrition Report](https://support.cronometer.com/hc/en-us/articles/360018569691-Nutrition-Report))
- Lesson for this vault: the closed Day is the same idea as "Complete Day." Average only over closed Day nodes. Say how many days the average covers.

### Weekly window versus rolling window

- Users asked for "rolling averages of various metrics with custom rolling windows to smooth daily fluctuations." `[user feedback]` ([Cronometer forum, Rolling Averages](https://forums.cronometer.com/discussion/4145/rolling-averages))
- A European user asked for weeks that start on Monday. Others: "does ANYONE actually like have their weekend view split up?" and frustration that the request is 5+ years open. `[user feedback]` ([Cronometer forum, week start on Monday](https://forums.cronometer.com/discussion/4052/web-calendar-week-start-on-monday))
- Lesson: default to a calendar week that starts on Monday. Offer "last 7 closed days" only when the user asks.

### Export and lock-in

- MyFitnessPal Data Export is for Premium subscribers, as CSV. Page returned 403 to my fetch; claim rests on the search snippet. `[vendor text]` ([MyFitnessPal help, Data Export FAQs](https://support.myfitnesspal.com/hc/en-us/articles/360032273352-Data-Export-FAQs))
- Cronometer forum users asked several times to import their MyFitnessPal history and could not. `[user feedback]` ([Cronometer forum, Import Data from MyFitnessPal](https://forums.cronometer.com/discussion/comment/122), [Bulk import](https://forums.cronometer.com/discussion/comment/5992))
- This vault is plain markdown in git. Lock-in does not apply. It is worth one line in the docs.

## 4. Recommended weekly review (chat only, closed Day nodes only)

Compute for the calendar week Monday to Sunday. Use only Day nodes with status `closed` or `auto-closed`.

1. **Days covered**: "6 of 7 days closed." Users complain most about averages that hide missing days, so state the count first.
2. **Average per day versus target**: calories and protein on one line, then fat, carbs, fiber, sugar, salt on a second line. Users say they judge the week by its average, not by each day.
3. **Days on target**: "4 of 6 days on target." The verdict is already stored at close, so this costs nothing and answers the user's own question.
4. **Most common miss**: "protein low on 3 days." One pattern is actionable; a list of every daily miss is the red-number problem again.
5. **Protein days at or above min**: "5 of 6." Protein is the one macro users check for consistency, and the 2018 cohort shows a flat week beats a saw-tooth week.

Do not add: streaks, colours, a calorie bank, a carry-over, charts, or a message about a bad day. A monthly review uses the same five lines over the calendar month.

## Unverified

- Reddit threads (r/loseit, r/MacroFactor, r/CICO, r/xxfitness, r/gainit): my tools cannot fetch reddit.com. Web search returned no Reddit pages for any query. All Reddit evidence is missing.
- MyFitnessPal community threads: pages render by JavaScript and the API returned 404/503. Only titles were readable. Bodies of "Lost my streak", "Weekly calorie deficit", "how to see weekly calorie average" and "For those tracking calories by weekly totals" are unread.
- Users reported self-punishment with exercise after a red number of 50 calories over. Seen only in a search snippet; source page not fetched.
- Patel et al. 2019 (J Behav Med): consistent trackers (≥6 of 7 days in ≥75% of weeks) lost about 2.4 kg more at 3 months. Springer redirected to a login. Numbers rest on a search snippet.
- Harvey et al. 2019 "What Matters in Weight Loss?", Carter et al. "My Meal Mate" patterns, Payne 2022 (Obesity Science & Practice): Europe PMC and PMC returned 503 or a captcha. Not read.
- HealthUnlocked threads ("ignore the daily up and down", "can you have one bad day a week"): 403. Not read.
- No direct user quote for "too many charts" was found. The claim rests on users choosing simpler external tools.
- MyFitnessPal Weekly Digest content: 403. Not read.

## Sources

User feedback:

- https://forums.cronometer.com/discussion/3756/how-well-do-you-hit-the-daily-targets
- https://forums.cronometer.com/discussion/comment/18396
- https://forums.cronometer.com/discussion/comment/21242
- https://forums.cronometer.com/discussion/comment/11672
- https://forums.cronometer.com/discussion/comment/13128
- https://forums.cronometer.com/discussion/comment/5539
- https://forums.cronometer.com/discussion/5792/streaks
- https://forums.cronometer.com/discussion/650/mark-days-as-not-tracked-for-averages
- https://forums.cronometer.com/discussion/5896/days-which-i-log-no-data-getting-used
- https://forums.cronometer.com/discussion/6933/what-is-the-benefit-purpose-to-mark-day-complete
- https://forums.cronometer.com/discussion/4145/rolling-averages
- https://forums.cronometer.com/discussion/562/rolling-average-weight-graphs-a-la-hacker-039-s-diet-trendweight
- https://forums.cronometer.com/discussion/4052/web-calendar-week-start-on-monday
- https://forums.cronometer.com/discussion/comment/122
- https://forums.cronometer.com/discussion/comment/5992
- https://community.myfitnesspal.com/en/discussion/10297030/lost-my-streak (title only)
- https://news.ycombinator.com/item?id=39301552
- https://news.ycombinator.com/item?id=44220135
- https://jeremylundmark.substack.com/p/the-uncredible-way-i-lost-40-pounds

Research papers:

- Eikey EV. Effects of diet and fitness apps on eating disorder behaviours: qualitative study. BJPsych Open, 2021. https://www.cambridge.org/core/journals/bjpsych-open/article/effects-of-diet-and-fitness-apps-on-eating-disorder-behaviours-qualitative-study/2D1EE739D97AB3EFC6573835E4C527BD
- Hill C et al. Relationship Between Weekly Patterns of Caloric Intake and Reported Weight Loss Outcomes. JMIR mHealth, 2018. DOI 10.2196/mhealth.8320. https://doaj.org/article/7c2ff48fae2c4e5b8305caf95b154415
- Burke LE et al. Adherence to self-monitoring and behavioral goals is associated with improved weight loss in an mHealth RCT. Obesity, 2025. DOI 10.1002/oby.24234. https://onlinelibrary.wiley.com/doi/full/10.1002/oby.24234
- Patel ML et al. Comparing Self-Monitoring Strategies for Weight Loss in a Smartphone App: RCT. JMIR mHealth, 2019. https://pmc.ncbi.nlm.nih.gov/articles/PMC6416539/

Vendor text:

- https://support.cronometer.com/hc/en-us/articles/360018569691-Nutrition-Report
- https://help.macrofactorapp.com/en/articles/21-weight-trend
- https://apps.apple.com/us/app/macrofactor-macro-tracker/id1553503471
- https://support.myfitnesspal.com/hc/en-us/articles/360032273352-Data-Export-FAQs
