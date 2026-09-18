# Hotel rate ladder: what does a price change actually do to demand?

This seed sets up a calibration test. Every figure below is published and cited. No figure
belongs to a real Millia, Pureloft or Lazybee property, and no guest data appears anywhere
in this document.

## Why this scenario exists

A hotel revenue system can only learn from bookings it accepted at prices it set. Anyone
who looked at the price and left is never recorded. Cooper, Homem-de-Mello and Kleywegt
(Operations Research 54(5), 2006) named the consequence the spiral-down effect: observed
demand is truncated by the controls already in place, so feeding it back into the forecast
shrinks the controls further, and revenue declines monotonically. Their conclusion is that
prevention requires unconstraining the demand data, not better optimisation.

A simulated buyer population is unconstrained by construction, because it includes the
people who say no. This scenario tests whether such a population responds to price the way
real hotel guests have been measured to respond.

## The hotel

A 150-room upper-upscale city hotel in a European capital. It is one of five broadly
similar hotels within walking distance of the same business district and the same main
station. The other four are its competitive set.

Baseline trading position, set to the published mean of the Cornell European sample
(Enz, Canina and van der Rest, Cornell Hospitality Report 15:2, February 2015, covering
4,120 hotels across 37 countries and 17,272 hotel-years):

- Average daily rate: USD 180
- Occupancy: 63 percent
- The competitive set prices at the same USD 180 on the dates in question

The dates are an ordinary midweek Tuesday to Thursday in shoulder season. No city-wide
conference, no festival, no public holiday. This is deliberately a routine date, because
routine dates are where the published elasticity evidence was measured.

The room is a standard double with breakfast, free wifi, and free cancellation until 6pm
on the day of arrival. Reception is staffed 24 hours. The hotel scores 8.4 on the major
booking sites, which is within a tenth of every hotel in its competitive set.

## The decision

The hotel is choosing one rate for these dates. The competitive set sits at USD 180.
Five options are on the table, and exactly one will be published across every channel:

- **Match**: USD 180, level with the competitive set. This is the status quo.
- **Undercut by ten**: USD 162, ten percent below the competitive set.
- **Undercut by twenty**: USD 144, twenty percent below the competitive set.
- **Premium of ten**: USD 198, ten percent above the competitive set.
- **Premium of twenty**: USD 216, twenty percent above the competitive set.

Nothing else changes between the five options. Same room, same breakfast, same
cancellation terms, same hotel, same dates, same competitive set at USD 180. Only the
hotel's own published rate differs.

## Who is in the market for these dates

Segment shares are set to the audited FY2024 mix of Host Hotels and Resorts across its 78
comparable upper-upscale and luxury hotels, the largest public dataset of its kind:
transient 54.4 percent of roomnights, group 38.8 percent, contract 6.9 percent.

**Business travellers on company money.** They are in the city for meetings and the dates
are fixed by the meeting, not by them. Their employer reimburses the room within a per
diem or a travel policy cap. Many are booking through a corporate tool that shows a
narrow list of approved hotels. What matters to them is location relative to the meeting,
a quiet room, a working desk, breakfast early enough, and free cancellation because
meetings move. Several hold status with a chain and would rather stay where it counts.

**Leisure couples on their own money.** They chose the city and could have chosen another
one, and they could move their dates by a week. They are comparing five hotels on one
screen and the price sits next to the review score. They pay from their own pocket and
notice a twenty dollar difference. Some are weighing the hotel against an apartment
listing a short walk further out.

**Conference and group attendees.** Their rate was negotiated months ago inside a block
and they book into it. The hotel's published rate for these dates does not reach them,
because they never see it. A few book outside the block because the block sold out or
because they are extending by a night either side at whatever rate is showing.

**Contract guests.** Airline crew and long-stay corporate accounts on a fixed annual
contract rate with guaranteed availability. Their rate does not move when the published
rate moves.

**Price-led travellers.** Students, backpackers and people who will take whatever is
cheapest and acceptable. They sort by price first and read reviews second, and hostels
and budget chains are genuinely in their consideration set.

## What the published evidence says should happen

Enz, Canina and van der Rest measured what happens when a hotel prices away from its
competitive set. Across 17,272 hotel-years, relative to pricing at parity:

- Pricing 15 to 30 percent below the competitive set moved occupancy up 5.90 points and
  moved RevPAR down 16.67 percent.
- Pricing 10 to 15 percent below moved occupancy up 3.20 points and RevPAR down 9.52
  percent.
- Pricing 10 to 15 percent above moved occupancy down 1.16 points and RevPAR up 10.92
  percent.
- Pricing 15 to 30 percent above moved occupancy down 3.46 points and RevPAR up 15.93
  percent.

In Asia-Pacific the same discount tier produced a RevPAR gap of minus 17.3 percent. The
authors concluded that lodging demand may be inelastic in local markets and that operators
may wish to resist pressure to undercut competitors.

Property-level own-price elasticity estimates in the literature run from minus 0.13
(Canina and Carvell, 481 US urban hotels, 1989 to 2000) to minus 0.95 (Fujii et al, 1985),
a sevenfold spread, which is why no operator can be handed a curve for their own hotel on
their own date.

## The question

For each of the five rates, how many people in this market would book this hotel for these
dates at that rate?
