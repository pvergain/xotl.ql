#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.these
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License (GPL) as published by the Free
# Software Foundation;  either version 3 of  the  License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Created on May 24, 2012

r'''
Extends the :mod:`~xotl.ql.expressions` language to provide universal
accessors.

The :obj:`this` object stands for every object in the "universe" (e.g. the
index, the storage, etc.) :obj:`this` eases the construction of expressions
directly, and also provides a query language by means of Python's syntax for
:ref:`generator expressions <py:generator-expressions>` and list, and dict
comprehensions (we shall call them comprehensions).


An overview of the Query Language
=================================

The basic query language uses comprehensions to express both the SELECT part
and FILTER part of a query.

In a query (comprehension) `this` objects stand for the entire universe of
objects *unless otherwise restricted by filter expressions*. For instance::

    >>> from xotl.ql.expressions import count
    >>> parents = (parent for parent in this if count(parent.children) > 0)

may be used to select every object ``parent`` that has an attribute
``children`` that is a non-empty sequence of objects.

The class of :obj:`this` is a sub-class of :class:`These`.

:class:`!These` instances may be *named*, thus allowing to select different
objects in a single query. When used in comprehensions, `this` automatically
yields a single uniquely named :class:`These` instance. So, you don't need to
specify a name by your self::

    >>> p, c = next((parent.name, child.name) for parent in this
    ...                        if count(parent.children) > 0
    ...                        for child in parent.children)

In order to have explicitly named instances you may provide a name::

    >>> parent, child = this('parent'), this('child')
    >>> q = ((p.name, c.name) for p in parent
    ...            if count(p.children) > 0 for c in child)

Providing a name may ease debugging tasks, and clarify log messages.

Notice that if you create an expression outside the context of a comprehesion
you **must** provide names for instances that refer to different objects.
Otherwise the expression would not express what you intended. For instance::

    >>> from xotl.ql.expressions import in_
    >>> parent, child = this, this
    >>> expr = in_(child, parent.children)
    >>> expr2 = in_(child, this.children)

Both ``expr`` and ``expr2`` are semantically equivalent::

    >>> with context(UNPROXIFING_CONTEXT):
    ...    expr == expr2
    True

And you may see that the "natural" meaning of ``expr2`` entails "objects that
are child of themselves", and that's probably not what we intended to express
with ``expr``.

Providing names avoids the confusion::

    >>> parent, child = this('parent'), this('child')
    >>> expr = in_(child, parent.children)
    >>> with context(UNPROXIFING_CONTEXT):
    ...    expr == expr2
    False


`this` properties
=================

.. autoclass:: These
   :members: name, parent, binding, root_parent


`this` is never bound
---------------------

Although :class:`These` instances may be automatically bound to expressions
inside comprehensions, the :obj:`this` object is never bound to any
expression, since this object is a singleton, and which may appear in
comprehesions, that behaves more like lambdas with a single argument.

For instance in the query::

    >>> from xotl.ql.expressions import all_
    >>> who = query(who for who in this if all_(who.children, this.age > 5))

that retrieves all object whose children are all beyond 5 years of age.


Subqueries
==========

.. note:: Work in progress.

::

    >>> from xotl.ql.expressions import is_a, all_, in_

    >>> who = query(who for who in this('w')
    ...                if all_(who.children,
    ...                        in_(this, query(sub for sub in this('s')
    ...                                         if is_a(sub, 'Subscritor')))))

    >>> str(unboxed(who).binding)
    "all(this('w').children, (in(this, this('s'))))"

.. _binding:

The intended meaning of bound `this` instances
----------------------------------------------

In a comprehension what is actually return is a (tuple of) named :class:`These`
instances; probably related through it's `parent` attribute, and probably
*bound* to the expressions in the IF part of the comprehension. If the filters
of a comprehensions involve a `These` instance, then it gets automatically
bound to the resulting expression.

When an instance of :class:`!These` is bound, query builders **should** yield
only those objects that satisfy the bound expression as substitutes for the
`this` instance.

Let's illustrate this with a universe that contains objects of any of the
following types::

    >>> class Person(object):
    ...    name = None
    ...    birth_date = None
    ...
    ...    @property
    ...    def age(self):
    ...        from datetime import datetime
    ...        return datetime.now() - self.birth_date

    >>> class Book(object):
    ...    title = None
    ...    published_date = None
    ...
    ...    @property
    ...    def age(self):
    ...        from datetime import datetime
    ...        return datetime.now() - self.published_date


If the universe is composed of objects that have the structure indicated by
those classes (that in this context may be seen like weak schemas); and we have
the query::

    >>> some = (some for some in this if some.age > 50)

When actually querying a datastore with this query, it would yield every object
no matter if a Person of a Book, whose ``age`` property has a value greater
than 50.

.. _binding-to-schemas:

Binding to schemas
~~~~~~~~~~~~~~~~~~

In the previous example, if we really need to filter by type, then we could
simply do::

    >>> older = next(some for some in this('any') if some.age > 50)
    >>> from xotl.ql.expressions import is_instance
    >>> books = query(book for book in older if is_instance(book, Book))
    >>> people = query(who for who in older if is_instance(who, Person))

As you may see in this example, you may reuse the ``older`` query to obtain
the two others, and they won't be confused::

    >>> str(unboxed(books).binding)  # doctest: +ELLIPSIS
    "(this('any').age > 50) and (is_a(this('any'), <class '...Book'>))"

    >>> str(unboxed(people).binding)  # doctest: +ELLIPSIS
    "(this('any').age > 50) and (is_a(this('any'), <class '...Person'>))"

.. warning:: You **should** use the function :func:`query` if you want to reuse
             queries. See the :ref:`note on reusability <reusability>`.

The rules to determine if an instance of :class:`These` is bound to a schema
are still in development. The intention is to inspect the AST for
``is_instance`` nodes and try to figure out the schema from those clues. But
since expressions are very powerful this is a task that may be undecidable.
Even the question of decidability is open for us. In any case, that problem is
for the *query translator* to tackle.

In fact, we also think of other clues that may taken into account:

- If the instance is compared by any of ``==``, ``<``, ``>``, ``<=``, ``>=`` to
  a number (or other instance/expression that should be a number), then it's
  probably a number.

- If the instance is compared with a string (or other instance/expression that
  should be a string), then it's probably a string.

- If the instance is counted with :class:`~xotl.ql.expressions.count`
  then it's a collection of other objects. Notice that this language may so
  powerful that we're tempted to allow constructions like::

      >>> a, b = next((count(count(parent.children) % 2 == 0),
      ...               count(count(parent.children) % 2 != 0))
      ...              for parent in this)

- If the instance is used as the first argument to
  :class:`~xotl.ql.expressions.startswith`,
  :class:`~xotl.ql.expressions.endswith` or
  :class:`~xotl.ql.expressions.length`, then it's probably a string.

- If the instance is an operand of ``+``, ``-`` or any other "arithmetical"
  operator and the second operand is a number, then it's probably a number.

Of course the previous rules are just proposals. Whether or not they are
included in the "final" release of any query translator, it's not decided.

.. note::

   It's proposed that OMCaF's schemas will also be able to be "queried"
   directly with the idiom::

        books = next(book for book in Book if book.age > 50)


Some limitations of the language
================================

.. _reusability:

1. Needs a double call to next for generator expressions if you're reusing a
   previous query (with bindings).

   If you write queries as generator expressions (and not list comprehensions
   or dict comprehensions) you **may have to** call next two times. If you
   don't, reutilisation of previous queries will fail to apply the autobinding
   properly::

        >>> older = next(what for what in this('any') if what.age > 10)
        >>> books_query = (book for book in older if is_instance(book, 'Book'))
        >>> books = next(books_query)

        >>> str(unboxed(books).binding)
        "is_a(this('any'), Book)"

   Notice that there's no condition upon age, and it should be. Calling next
   once more, solves the issue::

        >>> next(books_query, 'None')
        'None'

        >>> str(unboxed(books).binding)
        "(this('any').age > 10) and (is_a(this('any'), Book))"

   The function :func:`query` takes this step so you don't have to do it
   yourself::

        >>> books = query(book for book in older if is_instance(book, 'Book'))
        >>> str(unboxed(books).binding)
        "(this('any').age > 10) and (is_a(this('any'), Book))"


2. When expressions (not these instances) are involved in the selection part
   of the comprehension like in::

        >>> age, parent = next((parent.age + 10, parent)
        ...                        for parent in this('parent')
        ...                        if parent.age > 32)

   You must use the function :func:`query` to process the query, otherwise
   the `parent` instance will have the wrong binding::

        >>> unboxed(parent).binding    # doctest: +ELLIPSIS
        <expression 'this('parent').age + 10' ...>

   The function :func:`query` extracts the previous bindings and restores the
   proper one::

        >>> age, parent = query((parent.age + 10, parent)
        ...                        for parent in this('parent')
        ...                        if parent.age > 32)

        >>> unboxed(parent).binding    # doctest: +ELLIPSIS
        <expression 'this('parent').age > 32' ...>


3. We don't support spliting of conditions over the same (root) `this`
   instance in several IF clauses::


        >>> parent = query(parent for parent in this('parent')
        ...                    if parent.age > 30
        ...                    if parent.age < 45
        ...                    if parent.first_child.age > 10)

        >>> unboxed(parent).binding    # doctest: +ELLIPSIS
        <expression 'this('parent').first_child.age > 10' ...>

   Notice that all conditions over `parent.age` are lost, and the only
   condition that is bound to `parent` is the last one. In order to express
   what you want you may either, split the query in several queries like::

        >>> age30 = next(parent for parent in this('parent')
        ...                if parent.age > 30)

        # You **must** use query on the following, or use the double-next
        # call explained above.
        >>> age40 = query(parent for parent in age30 if parent.age < 40)
        >>> parent = query(parent for parent in age40
        ...                    if parent.first_child.age > 10)

        >>> unboxed(parent).binding # doctest: +ELLIPSIS
        <expression '((this('parent').age > 30) and (this('parent').age < 40)) and (this('parent').first_child.age > 10)' ...>

   or you may, write the whole condition in a single IF::

        >>> parent = query(parent for parent in this('parent')
        ...                    if (parent.age > 30) & (parent.age < 40) &
        ...                       (parent.first_child.age > 10))

        >>> unboxed(parent).binding # doctest: +ELLIPSIS
        <expression '((this('parent').age > 30) and (this('parent').age < 40)) and (this('parent').first_child.age > 10)' ...>


   .. warning::

      Since bindings are always applied to the top-most parent of a this
      instance you **must** observe this rule when double-looping over
      instances attributes, like in::

          >>> parent, child = query((parent, child) for parent in this('p')
          ...                            if parent.age > 20
          ...                            for child in parent.children
          ...                            if child.age < 10)

          >>> unboxed(parent).binding  # doctest: +ELLIPSIS
          <expression 'this('p').children.age < 10' ...>

      Like in the other examples, the `parent.age > 20` is lost. The fix is
      simple::

          >>> parent, child = query((parent, child) for parent in this('p')
          ...                            for child in parent.children
          ...                            if (parent.age > 20) &
          ...                               (child.age < 10))

          >>> unboxed(parent).binding  # doctest: +ELLIPSIS
          <expression '(this('p').age > 20) and (this('p').children.age < 10)' ...>

4. On the other hand, you **should** split conditions over differents
   instances of this. Otherwise, you may get more conditions that those that
   you expect::

        >>> person, book = query((person, book) for person in this('person')
        ...                        for book in this('book')
        ...                        if (person.age > 18) &
        ...                           (book.owner == person))

        >>> unboxed(person).binding  # doctest: +ELLIPSIS
        <expression '(this('person').age > 18) and (this('book').owner == this('person'))' ...>

        >>> unboxed(book).binding   # doctest: +ELLIPSIS
        <expression 'this('book').owner == this('person')' ...>

   As you may see, there're conditions over `person` that doesn't really
   matter. They may work, though. Spliting the conditions solves this over-
   conditioning issue::

        >>> person, book = query((person, book) for person in this('person')
        ...                        if person.age > 18
        ...                        for book in this('book')
        ...                        if book.owner == person)

        >>> unboxed(person).binding  # doctest: +ELLIPSIS
        <expression 'this('person').age > 18' ...>

   A better way for the previous would be::

        >>> person_books = query({person: book for person in this('person')
        ...                        if person.age > 18
        ...                        for book in this('book')
        ...                        if book.owner == person})

  When properly translated this query *should* always return a grouping, each
  group key should be an instance of every object that matches
  `this('person')`, and the values should be (a list) of that persons books.


5. Bindings are only placed to left-side instances. If in the example of
   `people`'s  `book`s if we swap operands in ``book.owner == person``, the
   bindings would be done to `person` instead. So::


        >>> person, book = query((person, book) for person in this('person')
        ...                        for book in this('book')
        ...                        if (person.age > 18) &
        ...                           (person == book.owner))

        >>> unboxed(person).binding  # doctest: +ELLIPSIS
        <expression '(this('person').age > 18) and (this('person') == this('book').owner)' ...>

        >>> unboxed(book).binding is None
        True


6. You can't invoke arbitrary functions inside query comprehensions.

   This has to do with two competing factors: technical difficulty to achieve
   in a general and portable way; and the expected benefits from doing so.

   The technical difficulty has to do with the way auto-binding of expressions
   is done in :class:`These` instances.

   We are not hacking the compiler's way of parsing the comprehension, but we
   use an :mod:`execution context <xoutil.context>` to identify that such
   binding should happen automatically *whenever* the `These` instance is the
   "left" (or first) operand in an expression.

   Since calling a function is *not* part of the expression language (unless
   such a function follows the protocol of
   :class:`~xotl.ql.expressions.FunctorOperator`) we won't be able to build a
   expression from that call.

   For such a thing to happen we'd have to get the `code object` that
   generated the comprehension (for generator expression this is easily
   accomplished, in CPython at least, but for dict and list comprehensions
   this not easily done without imposing other constraints that affect other
   features). After getting the `code object` we could disassemble it and do
   some (hard to do) transformations to detect calling of a function, etc...
   All of this would only work reliably for a given implementation of Python
   (CPython, PyPy, Jython, IronPython, other) because they may use different
   assembly code or something. So this would hinder portability across the
   Python ecosystem.

   On the other hand, we strongly believe that allowing to call arbitrary
   functions inside expressions won't yield a benefit proportional to the
   amount of work needed. This is not saying that calling function is not
   useful at all, but that allowing the invocation of *arbitrary* functions is
   much more costly than the gains obtained.

   If the function is used in the "select" part of the query you may easily
   post-process the results to apply the function after you get the results
   from the store. Anyway its likely that your arbitrary function is not
   translatable to the query language of the real data store, and if we allow
   you to put it in the query, we would have to do the same: post-process the
   results obtained from the store and then hand them to you. If the function
   *is* translatable to the data-store, then is likely that it *is also*
   possible to express it in the terms of the expression language.

   If the function is used in the "if" part of the query the query the same
   argument applies: if it's translatable, is likely that it may be put into
   the terms of the expression language.

   This does not prohibit invoking functions inside query comprehensions, but
   invoking *arbitrary* functions. Functions that return expressions should be
   fine most of the time::

       >>> from xotl.ql.expressions import count

       >>> old_enough = lambda who: who.age > 30
       >>> count_children = lambda who: count(who.children)

       >>> who, children = query((who, count_children(who))
       ...                         for who in this('who')
       ...                           if old_enough(who))

       >>> binding = unboxed(who).binding
       >>> str(binding)
       "this('who').age > 30"

       >>> str(children)
       "count(this('who').children)"


   To ease your anger at this decision, the expression language supports and
   :class:`~xotl.ql.expressions.call` that allows to express the we should
   call an arbitary function. But we strongly discourage its use, and is
   possible that some query translators/executors don't support that feature
   that always implies post-processing the results.


Ideas of expressions/queries inside model descriptions
======================================================

When defining the structure of an object, one should be allowed to declare an
attribute that is a query::

    class Person(SomeSchemaBase):
        name = str
        books = query(book for book in this
                        if is_instance(book, Book) & (book.owner == this))

In this case (if such thing is ever implemented), the :obj:`this` object
should be sustituted by the instance of `Person` that is being queried, i.e,
when executing::

    for book in person.books:
        pass

The resulting elements should be same as when executing::

    for book in fetch(book for book in this
                        if is_instance(book, Book) & (book.owner == person)):
        pass

Of course `SomeSchemaBase` would have to do some magic for this kind of
attribute to work.


On the processing of these queries
==================================

In it's most general form, what you get from calling :func:`query` is either:

- A single instance of a :class:`expressions
  <xotl.ql.expressions.ExpressionTree>` or a single instance of
  :class:`These`.

- A tuple/list of expressions and/or :class:`!These` instances.

- A dictionary whose sole key is an expression (or :class:`!These`) with its
  value as any of the two previous options.

Let's think on the processing of such a query and transforming it into a query
to a real database. Since our query language is abstracted from any kind of
structure, well-formed queries may become invalid for a given kind of
structured database.

Let's work with the same example in [Meijer2011]_. Suppose you have the
following SQLAlchemy definition of your objects following the declarative
style [#omcaf]_::

    >>> from sqlalchemy.ext.declarative import declarative_base
    >>> from sqlalchemy import Column, String, Integer
    >>> from sqlalchemy import Table, Text, ForeignKey
    >>> from sqlalchemy.orm import relationship, backref

    >>> Base = declarative_base()

    >>> products_keywords = Table('products_keywords', Base.metadata,
    ...                          Column('product_id', Integer,
    ...                                 ForeignKey('products.id')),
    ...                          Column('keyword_id', Integer,
    ...                                 ForeignKey('keywords.id')))

    >>> products_ratings = Table('products_ratings', Base.metadata,
    ...                          Column('product_id', Integer,
    ...                                 ForeignKey('products.id')),
    ...                          Column('rating_id', Integer,
    ...                                 ForeignKey('ratings.id')))

    >>> class Product(Base):
    ...    __tablename__ = 'products'
    ...
    ...    id = Column(Integer, primary_key=True)
    ...    title = Column(String)
    ...    year = Column(Integer)
    ...    pages = Column(Integer)
    ...    keywords = relationship('Keyword', secondary=products_keywords,
    ...                            backref='products')
    ...    ratings = relationship('Rating', secondary=products_ratings,
    ...                            backref='products')


    >>> class Keyword(Base):
    ...    __tablename__ = 'keywords'
    ...
    ...    id = Column(Integer, primary_key=True)
    ...    keyword = Column(String(50), nullable=False, unique=True)


    >>> class Rating(Base):
    ...    __tablename__ = 'ratings'
    ...
    ...    id = Column(Integer, primary_key=True)
    ...    rating = Column(String(50), nullable=False, unique=True)

In these representation we avoid putting more "database-centric" information
since they will not affect our thinking on how to translate a query like::

    >>> from xotl.ql.expressions import is_instance, any_
    >>> four_stars = query(product for product in this('p')
    ...                            if is_instance(product, Product) &
    ...                               any_(product.ratings,
    ...                                    this.rating == '****'))

    >>> str(unboxed(four_stars).binding)  # doctest: +ELLIPSIS
    "(is_a(this('p'), <class '...Product'>)) and (any(this('p').ratings, (this.rating == ****)))"


Notes
-----

.. [#omcaf] OMCaF will have it's own way to define schemas and OMCaF will rely
            on given implementations/configurations of persistence, so that
            mappers will be implicit.

The query function and the `this` object
========================================

.. autofunction:: query(expr for expr2 in expr3 if expr4 ...)


.. autodata:: this

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import)

import re
from itertools import count

from xoutil.objects import get_first_of, validate_attrs
from xoutil.context import context
from xoutil.decorators import assignment_operator
from xoutil.aop.basic import contextualized
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed

from xotl.ql.expressions import eq, ne, _true, _false, ExpressionTree
from xotl.ql.expressions import OperatorType, UNARY, BINARY



__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = (b'this',)




class _name(unicode):
    pass



class AUTOBINDING_CONTEXT(object):
    '''Context in which every expression involving a `this` instance is
    automatically bound to it.

    This context is applied when iterating over `this` instances::

        >>> from xotl.ql.these import this
        >>> expr = next(parent.age for parent in this('parent')
        ...                    if parent.age > 32)
        >>> str(unboxed(expr).binding)
        "this('parent').age > 32"
    '''


class TheseType(type):
    '''
    The type of the :class:`These` object.
    '''
    # TODO: Do we need to use threading.local?
    _instances = {}

    def __call__(self, name=None, **kwargs):
        '''
        Implements the singleton pattern avoiding calling __init__ if the
        object is reused instead of created.
        '''
        parent = kwargs.get('parent', None)
        if name and parent is None:
            parent = self()
        if (not context[AUTOBINDING_CONTEXT] and
                (parent, name) in TheseType._instances):
            return TheseType._instances[parent, name]
        else:
            result = self.__new__(self, name, **kwargs)
            with context(UNPROXIFING_CONTEXT):
                result.__init__(name, **kwargs)
            if not context[AUTOBINDING_CONTEXT]:
                # Do not substitute the singleton instance if we're in a
                # automutate context.
                TheseType._instances[parent, name] = result
            return result



def _update_autobound_instances(instance, who, expr1, res):
    with context(UNPROXIFING_CONTEXT):
        if isinstance(who, These):
            autobound = getattr(who, 'autobinding_instance',
                                None) or who
        else:
            assert isinstance(expr1, These)
            autobound = getattr(expr1, 'autobinding_instance',
                                None) or expr1
        instance.autobinding_instance = autobound
        if autobound.binding:
            # In order to restore previous bindings when there are expressions
            # in the SELECT part of a query, we keep previous bindings of the
            # instance. See the :func:`query` function.
            #
            # But if the previous bindings are the children of the current
            # binding, we just replace them.
            #
            # This is tricky to capture correctly, cause some one may do::
            #
            #        (1 + (p.age + 10) for p in this if p.age + 10)
            #
            # TODO: [URGENT] Rethink!!!
            previous_bindings = autobound.previous_bindings
            children = autobound.binding.children
            if previous_bindings:
                if autobound.binding.op._arity == UNARY:
                    if previous_bindings[-1] == children[0]:
                        previous_bindings.pop()
                elif autobound.binding.op._arity == BINARY:
                    if previous_bindings[-1] == children[1]:
                        previous_bindings.pop()
                    if (previous_bindings and
                        previous_bindings[-1] == children[0]):
                        previous_bindings.pop()
            autobound.previous_bindings.append(autobound.binding)
        autobound.binding = res
        instance.binding = res
        return autobound



def _build_this_unary_op(operation):
    from xotl.ql.expressions import _build_unary_operator
    _method = _build_unary_operator(operation)
    def method(self):
        if not context[AUTOBINDING_CONTEXT]:
            return _method(self)
        else:
            expr1 = self
            with context(UNPROXIFING_CONTEXT):
                if isinstance(self, _AutobindingThese):
                    who = self.binding
                else:
                    who = self
                name = 'autobinding_hack' + self._newname()
            res = _method(who)
            # See the note on the binary method
            instance = _AutobindingThese(name=name, parent=None)
            _update_autobound_instances(instance, who, expr1, res)
            return instance
    method.__name__ = _method.__name__
    return method


def _build_this_binary_op(operation):
    from xotl.ql.expressions import _build_binary_operator
    _method = _build_binary_operator(operation)
    def method(self, other):
        if not context[AUTOBINDING_CONTEXT]:
            return _method(self, other)
        else:
            expr1 = self
            expr2 = other
            with context(UNPROXIFING_CONTEXT):
                root_parent = self.root_parent
                if isinstance(self, _AutobindingThese):
                    who = self.binding
                else:
                    who = self
                name = 'autobinding_hack' + self._newname()
                if isinstance(other, _AutobindingThese):
                    expr2 = other.binding or other
            res = _method(who, expr2)
            # To correctly implement the (parent.age >30) & (child.age < 5)
            # stuff, we need to return something different than self with its
            # binding, something that:
            #
            #   1. Behaves like a These instance
            #   2. Is bound solely to the resultant expression
            #   3. We can use it for extract the binding but later dispose
            #      of it.
            #
            # So, the solution seems to build a named These instance that is
            # not related to the real instance that is being changed. But since
            # the very first time, that instance is the `who` and we modify
            # `who`'s binding we're getting the expression built right.
            #
            # But that expression needs to be bound to the real instance.
            #
            # However, if who.root_parent is this, no autobinding should be
            # done. TODO: Change this type?
            if root_parent is not this:
                instance = _AutobindingThese(name=name, parent=None)
                _update_autobound_instances(instance, who, expr1, res)
                return instance
            else:
                return res
    method.__name__ = _method.__name__
    return method



_expr_operations = {operation._method_name:
                    _build_this_unary_op(operation)
                 for operation in OperatorType.operators
                    if getattr(operation, '_arity', None) == UNARY}
_expr_operations.update({operation._method_name:
                        _build_this_binary_op(operation)
                      for operation in OperatorType.operators
                        if getattr(operation, '_arity', None) is BINARY and
                           operation._method_name not in ('__eq__', '__ne__',
                                                          '__call__')})
TheseExpressionOperations = type(b'TheseExpressionOperations', (object,),
                                 _expr_operations)



_this_eq = _build_this_binary_op(eq)
_this_ne = _build_this_binary_op(ne)



@contextualized(context(UNPROXIFING_CONTEXT), TheseExpressionOperations)
class These(object):
    '''
    The type of :obj:`this` symbol: an unnamed object that may placed in
    queries and whose interpretation may be dependant of the query context and
    the context in which `this` symbol is used in the query itself.
    '''
    __metaclass__ = TheseType

    _counter = count(1)
    valid_names_regex = re.compile(r'^(?!\d)\w[\d\w_]*$')

    #: `These` instances may be named in order to be distiguishable from each
    #: other in a query where two instances may represent different objects.
    name = None

    #: `These` instances may have a parent `these` instance from which they
    #: are to be "drawn". If fact, only the pair of attributes
    #: ``(parent, name)`` allows to distiguish two instances from each other.
    parent = None


    def __init__(self, name=None, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self.validate_name(name)
            self.name = name
            self.parent = kwargs.get('parent', None)
            self._binding = []
            if not self.parent:
                self.bind(get_first_of(kwargs,
                                       'binding',
                                       'expression',
                                       'condition',
                                       'filter',
                                       default=None))


    def bind(self, expression):
        self.binding = expression


    @staticmethod
    def _compute_binding(res):
        head, tail = res[0], res[1:]
        if tail:
            from .expressions import and_
            return reduce(and_, tail, head)
        else:
            return head



    @property
    def previous_bindings(self):
        '''
        A list of previous bindings.

        When in the AUTOBINDING_CONTEXT, we keep temporarily keep these
        bindings, so that expressions may appear in the SELECT part of a
        comprehension.

        In a query like::

            >>> q = ((parent.age + 10, parent) for parent in this
            ...                if count(parent.children) > 5)

        The first selected element is a expression, but since every
        comprehesion is executed automatically inside the AUTOBINDING_CONTEXT,
        then `parent.age + 10` would be the binding for parent.

        That's why we need both this property and :func:`query` to restore the
        proper bindings for each instance.
        '''
        current, res = self, None
        who = current
        while current and not res:
            res = getattr(current, '_previous_bindings', None)
            current, who = current.parent, current
        if res is None:
            res = []
            setattr(who, '_previous_bindings', res)
            return res
        else:
            return res


    @property
    def root_parent(self):
        '''
        The top-most parent of the instace or self if it has no parent.
        '''
        if self.parent is not None:
            return self.parent.root_parent
        else:
            return self


    @property
    def binding(self):
        '''
        The expression to which the `These` instance is bound to or None.
        '''
        current, res = self, None
        while current and not res:
            res = getattr(current, '_binding', None)
            current = current.parent
        if res:
            return self._compute_binding(res)
        else:
            return None


    @binding.setter
    def binding(self, value):
        parent = getattr(self, 'parent', None)
        if parent:
            parent.binding = value
        else:
            self._binding = [value, ]


    @binding.deleter
    def binding(self):
        parent = getattr(self, 'parent', None)
        if parent:
            del parent.binding
        else:
            del self._binding


    @classmethod
    def _newname(cls):
        return _name('i{count}'.format(count=next(cls._counter)))


    @classmethod
    def validate_name(cls, name):
        '''
        Checks names of named These instances::

            >>> this('1nvalid')        # doctest: +ELLIPSIS
            Traceback (most recent call last):
                ...
            NameError: Invalid identifier '1nvalid' ...
        '''
        if name and not cls.valid_names_regex.match(name):
            raise NameError('Invalid identifier %r for a named These '
                            'instance' % name)


    def __getattribute__(self, attr):
        # Notice we can't use the __getattr__ way because then things like::
        #   this.name and this.binding
        # would not work properly.
        get = super(These, self).__getattribute__
        if attr in ('__mro__', '__class__', '__doc__',) or context[UNPROXIFING_CONTEXT]:
            return get(attr)
        else:
            return These(name=attr, parent=self)


    def __deepcopy__(self, memo=None):
        from copy import deepcopy
        with context(UNPROXIFING_CONTEXT):
            name = self.name or self._newname()
            parent = self.parent
            binding = deepcopy(self.binding, memo)
        return These(name, parent=parent, filter=binding)


    def __iter__(self):
        '''
        Yields a single instance of this but wrapped around an object that
        allows for conditions to be expressed upon this instance::

            >>> tuple(parent.age for parent in this)  # doctest: +ELLIPSIS
            (<this('i...').age at 0x...>,)


        This allows an idiomatic way to express retrievals from several types
        of models::

            >>> fetch = next    # Just to show off the idiom
            >>> fetch((parent, child)   # doctest: +ELLIPSIS
            ...            for parent in this('parent')
            ...            for child in parent.children)
            (<this('parent') ...>, <this('parent').children ...>)


        Furthermore, if should be natural to introduce conditions over the
        results. But the support for this to happen cannot be realiably
        introduced in here::

            >>> fetch(parent for parent in this('parent')  # doctest: +ELLIPSIS
            ...        if parent.age > 32)
            <this('parent') ...>
        '''
        with context(UNPROXIFING_CONTEXT):
            name = self.name or self._newname()
            parent = self.parent
            # TODO: Think if this necessary. The idea: In a query like:
            #            ((p, c) for p in this
            #                        if p.age > 30
            #                    for c in p.children)
            # In the second iter: does p.age > 30 is already bound to p (and
            # thus to p.children)?
            if parent is None:
                current_binding = self.binding
            else:
                current_binding = None
        with context(AUTOBINDING_CONTEXT):
            instance = These(name, parent=parent)
            assert instance is not self
            yield instance
        # If we are iterating over an instance with a binding we *must* respect
        # such binding, so we and-it after our own binding (if any).
        if current_binding:
            with context(UNPROXIFING_CONTEXT):
                if instance.binding:
                    instance.binding = current_binding & instance.binding
                else:
                    instance.binding = current_binding


    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            name = self.name
            parent = self.parent
        if parent is None and not name:
            return 'this'
        elif parent is None and name:
            return "this('{name}')".format(name=name)
        elif parent is not None and name:
            return "{parent}.{name}".format(parent=str(parent),
                                              name=name)
        else:  # parent and not name:
            assert False

    def __repr__(self):
        return '<%s at 0x%x>' % (str(self), id(self))


    def __eq__(self, other):
        '''
            >>> with context(UNPROXIFING_CONTEXT):
            ...    this('parent') == this('parent')
            True

            >>> from xotl.ql.expressions import _true
            >>> (this('parent') == this('parent')) is _true
            True
        '''
        with context(UNPROXIFING_CONTEXT):
            if isinstance(other, These):
                res = validate_attrs(self, other, ('name', 'parent',
                                                   'binding'))
            else:
                res = False
        if context[UNPROXIFING_CONTEXT]:
            return res
        else:
            if self is not other:
                return _this_eq(self, other)
            else:
                # In logic A == A is always true so we don't produce nothing
                # for it.
                return _true


    def __ne__(self, other):
        '''
            >>> with context(UNPROXIFING_CONTEXT):
            ...    this('parent') != this('parent')
            False

            >>> from xotl.ql.expressions import _false
            >>> (this('parent') != this('parent')) is _false
            True
        '''
        with context(UNPROXIFING_CONTEXT):
            if isinstance(other, These):
                res = validate_attrs(self, other, ('name', 'parent',
                                                   'binding'))
            else:
                res = False
        if context[UNPROXIFING_CONTEXT]:
            return not res
        else:
            if self is not other:
                return _this_ne(self, other)
            else:
                return _false


class _AutobindingThese(These):
    'Marker class for autobinding these instances in expressions inside a '
    'comprehension'



class ThisClass(These):
    '''
    The class for the :obj:`this` object.

    The `this` object is a singleton that behaves like any other :class:`These`
    instances but also allows the creation of named instances.

    '''

    def __call__(self, *args, **kwargs):
        return type(self)(*args, **kwargs)


#: The `this` object is a unnamed universal "selector" that may be placed in
#: expressions and queries.
this = ThisClass()



def _restore_binding(which):
    if isinstance(which, _AutobindingThese):
        with context(UNPROXIFING_CONTEXT):
            expression = which.binding
            instance = which.autobinding_instance
            previous_bindings = instance.previous_bindings
        with context(UNPROXIFING_CONTEXT):
            if previous_bindings:
                children = expression.children
                if expression.op._arity == UNARY:
                    if previous_bindings[-1] == children[0]:
                        previous_bindings.pop()
                elif expression.op._arity == BINARY:
                    if previous_bindings[-1] == children[1]:
                        previous_bindings.pop()
                    if (previous_bindings and
                        previous_bindings[-1] == children[0]):
                        previous_bindings.pop()
            if previous_bindings:
                instance.binding = previous_bindings[0]
            else:
                instance.binding = None
        return expression
    else:
        return which


def query(comprehesion):
    '''
    Process the result of a comprehension to restore proper bindings if
    expressions are involved in the selection part.

    '''
    import types
    assert isinstance(comprehesion, (types.GeneratorType, list, dict))
    if isinstance(comprehesion, types.GeneratorType):
        result = next(comprehesion)
        # We need to ask for the next so the post-yielding code is executed.
        none = next(comprehesion, None)
        assert none is None
        klass = type(result)
    elif isinstance(comprehesion, list):
        result = comprehesion[0]
        klass = list
    else:
        assert isinstance(comprehesion, dict)
        result = comprehesion
    if isinstance(result, (tuple, list)):
        with context(UNPROXIFING_CONTEXT):
            instances_to_restore = {i.autobinding_instance.root_parent
                                    for i in result
                                    if isinstance(i, _AutobindingThese)}
            expressions = {i.binding for i in result
                            if isinstance(i, _AutobindingThese)}
            for instance in instances_to_restore:
                for expr in expressions:
                    try:
                        instance.previous_bindings.remove(expr)
                    except:
                        pass
        if klass == tuple:
            return klass(_restore_binding(which) for which in result)
        else:
            # Possibly a namedtuple, but there's no way I can't tell.
            return klass(*(_restore_binding(which) for which in result))
    elif isinstance(result, dict):
        iterator = result.iteritems()
        key, value = next(iterator)
        none = next(iterator, None)
        assert none is None
        key = _restore_binding(key)
        if isinstance(value, tuple):
            value = tuple(_restore_binding(which) for which in value)
        elif isinstance(value, list):
            value = list(_restore_binding(which) for which in value)
        else:
            value = _restore_binding(value)
        return {key: value}
    else:
        return _restore_binding(result)



def thesefy(target):
    '''
    Takes in a class and injects it an `__iter__` method that can be used
    to form queries::

        >>> @thesefy
        ... class Person(object):
        ...    pass

        >>> q = query(who for who in Person if who.age > 30)
        >>> unboxed(q).binding    # doctest: +ELLIPSIS
        <expression '(is_a(this('...'), <class '...Person'>)) and (this('...').age > 30)' ...>

    This is only usefull if your real class does not have a metaclass of its
    own that do that.
    '''
    from xoutil.objects import nameof
    class new_meta(type(target)):
        def __new__(cls, name, bases, attrs):
            return super(new_meta, cls).__new__(cls, nameof(target), bases, attrs)
        def __iter__(self):
            from xotl.ql.expressions import is_a
            return iter(next(s for s in this if is_a(s, self)))
    class new_class(target):
        __metaclass__ = new_meta
    return new_class



# XXX: Util types for bound/unbound and named/unnamed this instances.
# TODO: Check whether we need this or not.

class _complementof(type):
    def __instancecheck__(self, instance):
        return not isinstance(instance, self.target)


@assignment_operator(maybe_inline=False)
def complementof(name, typ, doc=None):
    return _complementof(name,
                         (object,),
                         {'target': typ,
                          '__doc__': doc})


class _bound_type(type):
    def __instancecheck__(self, instance):
        with context(UNPROXIFING_CONTEXT):
            return (isinstance(instance, These) and
                    getattr(instance, 'binding', False))


class bound(object):
    '''
    Pure type for bound `this` instances::

        >>> isinstance(this, bound)
        False

        >>> who = next(parent for parent in this if parent.age > 32)
        >>> isinstance(who, bound)
        True
    '''
    __metaclass__ = _bound_type


unbound = complementof(bound)


class _named_type(type):
    def __instancecheck__(self, instance):
        with context(UNPROXIFING_CONTEXT):
            return (isinstance(instance, These) and
                    get_first_of(instance, 'name', '__name__', default=False))


class named(object):
    '''
    Pure type for named this instances::

        >>> isinstance(this, named)
        False

        >>> isinstance(this('parent'), named)
        True
    '''
    __metaclass__ = _named_type


unnamed = complementof(named)
