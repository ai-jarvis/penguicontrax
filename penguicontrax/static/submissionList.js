(function (ptrax) {

    function getCookieOrRandom(cname)
    {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for(var i=0; i<ca.length; i++)
          {
          var c = ca[i].trim();
          if (c.indexOf(name)==0) return c.substring(name.length,c.length);
          }
        return Math.floor(Math.random()*100000);
    }

    ptrax.model.Submissions = can.Model.extend({
        'findAll': "/api/submissions?state=0,1,2&ver=" + getCookieOrRandom('submission_ver')
    }, {});

    ptrax.model.RejectedSubmissions = can.Model.extend({
        'findAll': "/api/submissions?state=3&ver=" + getCookieOrRandom('submission_ver')
    }, {});

    ptrax.SubmissionList = can.Control.extend({
        defaults: {
            submissions: [],
            submissionsTpl: "",
            userLinkTpl: "",
            presenterLinkTpl: "",
            userTextTpl: ""
        }
    }, {

        init: function () {
            //register child views
            can.view.registerView('user_link', ptrax.util.tplDecode(this.options.userLinkTpl));
            can.view.registerView('presenter_link', ptrax.util.tplDecode(this.options.presenterLinkTpl));
            can.view.registerView('user_text', ptrax.util.tplDecode(this.options.userTextTpl));

            var renderer = can.view.mustache(ptrax.util.tplDecode(this.options.submissionsTpl));

            var fragment = renderer({
                submissions: this.options.submissions,
                user: ptrax.user
            }, {
                _followUpState: function () {
                    var state = ["submitted", "followedup", "accepted", "rejected"];
                    return state[this.attr('followUpState')];
                },
                _duration: function () {
                    var suffix = this.attr('duration') > 1 ? ' hrs' : ' hr';
                    if (this.attr('duration') == 4) {
                        return '4+ hrs';
                    } else if (this.attr('duration') == 5) {
                        return 'All wknd';
                    } else {
                        return this.attr('duration') + suffix;
                    }
                },
                num_rsvp: function () {
                    return '' + this['rsvped_by'].attr().length;
                },
                user_rsvp: function () {
                    var rsvps = this['rsvped_by'].attr();
                    return _.find(rsvps, {'id': ptrax.user.id }) ? 'fa-thumbs-up' : 'fa-thumbs-o-up';
                },
                submission_link : function(){
                    var text = this.title;
                    if(this.submitter){
                        if(ptrax.user.staff || (ptrax.user.id == this.submitter.id)){
                            text = '<a href="/eventform?id='+this.id+'" class="submission-link">'+this.title+'</a>'
                        }
                    }
                    return text;
                },
                _presenters: function () {
                    var presenters = this.attr('presenters');
                    var lastEl;
                    var names = _.pluck(presenters, 'name');
                    if (names.length > 1) {
                        lastEl = names[names.length - 1];
                        lastEl = "and " + lastEl;
                        names[names.length - 1] = lastEl;
                    }

                    if (names.length > 2) {
                        return names.join(", ");
                    } else {
                        return names.join(" ");
                    }
                },
                has_presenters: function() {
                    return this.attr('presenters').length > 0;
                }
            });

            this.element.html(fragment);
        },

        ".toggle-user-rsvp click": function (el) {
            var submission = el.data('submission');
            var user_rsvp = _.findIndex(submission.attr('rsvped_by'), {'id': ptrax.user.id });
            var apiUrl = '/api/submission/' + submission.attr('id') + '/rsvp';
            var $totalRsvpPointsElement = $('#totalRsvpPoints');

            if (ptrax.user.id === 0) {
                $('#login_modal_body').html('Please log in to indicate you <span class="fa fa-thumbs-o-up"></span> "Wouldattend" an event.');
                $('#login_modal').modal('show');
            } else {
                if (!submission.attr('updating')) {
                    submission.attr('updating', true);

                    if (user_rsvp < 0) {
                        //add it
                        $.ajax({
                            url: apiUrl,
                            type: 'POST',
                            success: function () {
                                submission['rsvped_by'].push(ptrax.user);
                                submission.attr('updating', false);
                                //Take one away from the rsvp points next to  the top thumbsup
                                $totalRsvpPointsElement.text(parseInt($totalRsvpPointsElement.text(),10)-1);
                            }
                        });
                    } else {
                        //if its is already there, take it out
                        $.ajax({
                            url: apiUrl,
                            type: 'DELETE',
                            success: function () {
                                //if its is already there, take it out
                                submission['rsvped_by'].splice(user_rsvp, 1);
                                submission.attr('updating', false);
                                //add one to the user rsvp points
                                $totalRsvpPointsElement.text(parseInt($totalRsvpPointsElement.text(),10)+1);
                            }
                        });
                    }
                }
            }
        }

    });

})(window.ptrax);
